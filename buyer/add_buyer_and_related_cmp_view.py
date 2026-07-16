from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import os
import pandas as pd

from supplier.models import Sell_products
from buyer.models import buyer_details, Buyer_contact_details, Buyer_addresses, Buyer_media, Purchase_products

BUYER_FIELDS = [
    'Description', 'Website_link', 'GST_number', 'IEC_code',
    'PAN_number', 'DIN_number', 'CIN_number', 'DUNS_number',
    'Contact_person', 'Payment_terms', 'Supplier_preferences',
    'Transport_preferences', 'Monthly_requirements',
    'WCPD_code', 'Admin_remark',
]

_recipe_df = pd.read_excel(
    os.path.join(settings.STATICFILES_DIRS[0], 'recipe_pairs_all_categories.xlsx')
)
_category_list = sorted(_recipe_df['Category'].dropna().unique().tolist())

def add_buyer(request):
    if request.method == 'POST':
        company_name = request.POST.get('Company_name', '').strip()
        if not company_name:
            messages.error(request, 'Company name is required.')
            return render(request, 'suppliers/supplier_add.html')

        with transaction.atomic():
            buyer = buyer_details.objects.create(
                Company_name=company_name,
                Created_at=timezone.localdate(),
            )

            # scalar fields
            for field in BUYER_FIELDS:
                val = request.POST.get(field, '').strip()
                if val:
                    setattr(buyer, field, val)
            buyer.save()

            # contacts
            for email in request.POST.getlist('Email'):
                if email.strip():
                    Buyer_contact_details.objects.create(Buyer = buyer, Email=email.strip())
            for phone in request.POST.getlist('Phone'):
                if phone.strip():
                    Buyer_contact_details.objects.create(Buyer = buyer, Phone=phone.strip())
            for fax in request.POST.getlist('FAX'):
                if fax.strip():
                    Buyer_contact_details.objects.create(Buyer = buyer, FAX=fax.strip())

            products = request.POST.getlist('Product')
            sectors = request.POST.getlist('Sector')
            divisions = request.POST.getlist('Division')
            product_groups = request.POST.getlist('Product_group')
            product_categories = request.POST.getlist('Product_category')
            HSN_code = request.POST.getlist('HSN_code')
            billing_addresses = request.POST.getlist('Billing_address')
            delivery_addresses = request.POST.getlist('Delivery_address')

            for i, prd in enumerate(products):
                if prd.strip():
                    Purchase_products.objects.create(
                        Buyer = buyer,
                        Sector = sectors[i].strip() if i < len(sectors) else '',
                        Division = divisions[i].strip() if i < len(divisions) else '',
                        Product_group = product_groups[i].strip() if i < len(product_groups) else '',
                        Product_category = product_categories[i].strip() if i < len(product_categories) else '',
                        Product = prd.strip(),
                        HSN_code = HSN_code[i].strip() if i < len(HSN_code) else '',
                        Billing_address = billing_addresses[i].strip() if i < len(billing_addresses) else '',
                        Delivery_address = delivery_addresses[i].strip() if i < len(delivery_addresses) else '',
                    )

            # addresses — form posts parallel lists: Address[], City[], State[], Country[]
            addresses   = request.POST.getlist('Address')
            cities      = request.POST.getlist('City')
            states      = request.POST.getlist('State')
            countries   = request.POST.getlist('Country')
            for i, addr in enumerate(addresses):
                if addr.strip():
                    Buyer_addresses.objects.create(
                        Buyer=buyer,
                        Address=addr.strip(),
                        City=cities[i].strip()    if i < len(cities)    else '',
                        State=states[i].strip()   if i < len(states)    else '',
                        Country=countries[i].strip() if i < len(countries) else '',
                    )

            # documents & images
            for doc in request.FILES.getlist('documents'):
                Buyer_media.objects.create(Buyer=buyer, Document=doc)
            for img in request.FILES.getlist('images'):
                Buyer_media.objects.create(Buyer=buyer, Image=img)

        messages.success(request, f'Buyer "{company_name}" added successfully.')
        return redirect('buyer:buyer_list')
    
    context = {
        'category_list': _category_list,
    }

    return render(request, 'add_buyer.html',context)

def related_sellers(request, bu_id):
    """
    For an enquiry, find:
    1. Direct sellers — suppliers who sell the exact products in the enquiry.
    2. Indirect/upstream sellers — suppliers who sell raw materials that are
       inputs to the enquired products (via DGFT SION recipe data).
    """
    buyer  = get_object_or_404(buyer_details, id=bu_id)
    products = Purchase_products.objects.filter(Buyer=buyer).exclude(Product='')

    product_name = [p.Product.strip() for p in products if p.Product.strip()]

    direct_qs = Sell_products.objects.filter(Product__in=product_name
        ).select_related('Supplier').exclude(Product='')

    direct_map = {}   # supplier_id -> {supplier, matched_products}
    for sp in direct_qs:
        sid = sp.Supplier.id
        if sid not in direct_map:
            direct_map[sid] = {'supplier': sp.Supplier, 'matched_products': []}
        direct_map[sid]['matched_products'].append(sp.Product)

    direct_sellers = list(direct_map.values())

    # ── 2. Indirect/upstream sellers ──
    # Step 1: which input items go INTO the enquired products?
    df = _recipe_df.copy()
    df['Output Item'] = df['Output Item'].str.strip()
    df['Input Item']  = df['Input Item'].str.strip()

    mask         = df['Output Item'].isin(product_name)
    recipe_rows  = df[mask][['Output Item', 'Input Item']].drop_duplicates()

    indirect_sellers = []
    if not recipe_rows.empty:
        # build lookup: input_item -> list of enquired output products that need it
        input_to_outputs = (
            recipe_rows
            .groupby('Input Item')['Output Item']
            .apply(list)
            .to_dict()
        )
        print(input_to_outputs)
        raw_material_names = list(input_to_outputs.keys())
        print(raw_material_names)

        # Step 2: find suppliers who sell those raw materials
        indirect_qs = Sell_products.objects.filter(
            Product__in=raw_material_names
        ).select_related('Supplier').exclude(Product='')

        # exclude suppliers already in direct_sellers
        direct_ids = set(direct_map.keys())

        indirect_map = {}  # supplier_id -> {supplier, sells_raw_materials, for_enquired_products}
        seen_pairs   = set()
        for sp in indirect_qs:
            if sp.Supplier.id in direct_ids:
                continue
            sid  = sp.Supplier.id
            pair = (sid, sp.Product.strip())
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            product = sp.Product.strip().upper()
            temp_input_to_outputs = {k.upper(): (i.upper() for i in v) for k, v in input_to_outputs.items()}
            
            outputs = [str(o) for o in temp_input_to_outputs.get(product, [])]

            if sid not in indirect_map:
                indirect_map[sid] = {
                    'supplier':            sp.Supplier,
                    'sells_raw_materials': [],
                    'for_enquired_products': set(),
                }
            indirect_map[sid]['sells_raw_materials'].append(sp.Product)
            indirect_map[sid]['for_enquired_products'].update(outputs)

        for v in indirect_map.values():
            v['for_enquired_products'] = list(v['for_enquired_products'])
        indirect_sellers = list(indirect_map.values())

    return render(request, 'related_sellers.html', {
        'buyer':            buyer,
        'direct_sellers':   direct_sellers,
        'indirect_sellers': indirect_sellers,
    })