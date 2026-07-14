from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from buyer.models import buyer_details
from enquiry.models import Enquiry_details, Enquiry_products, Enquiry_media
from supplier.models import Sell_products
import pandas as pd, os
from django.conf import settings
from django.utils import timezone

# ── load recipe data once ──
_recipe_df     = pd.read_excel(os.path.join(settings.STATICFILES_DIRS[0], 'recipe_pairs_all_categories.xlsx'))
_category_list = sorted(_recipe_df['Category'].dropna().unique().tolist())

PRODUCT_FIELDS = [
    'Sector', 'Division', 'Product_group', 'Product_category',
    'HSN_code', 'Quantity', 'Packaging', 'Currency',
    'Billing_address', 'Delivery_address',
]

ENQUIRY_SCALAR_FIELDS = [
    'Enquiry_type', 'Admin_remark', 'Description',
]

EXCEL_COMPANY_FIELDS = [
    'Company_name', 'Enquiry_type', 'Admin_remark', 'Description',
]

EXCEL_PRODUCT_FIELDS = PRODUCT_FIELDS + ['Product', 'Target_price']

def add_enquiry(request):
    if request.method == 'POST':
        mode = request.POST.get('buyer_mode', 'existing')

        with transaction.atomic():
            enquiry = Enquiry_details()

            if mode == 'existing':
                buyer_id = request.POST.get('buyer_id', '').strip()
                if not buyer_id:
                    messages.error(request, 'Please select an existing buyer or switch to manual entry.')
                    return _render_add(request)
                buyer = get_object_or_404(buyer_details, id=buyer_id)
                enquiry.buyer        = buyer
                enquiry.Company_name = buyer.Company_name
            else:
                company_name = request.POST.get('Company_name', '').strip()
                if not company_name:
                    messages.error(request, 'Company name is required.')
                    return _render_add(request)
                enquiry.Company_name = company_name

            enquiry.Description  = request.POST.get('Description', '').strip()
            enquiry.Enquiry_date = request.POST.get('Enquiry_date') or None
            enquiry.Closing_date = request.POST.get('Closing_date') or None
            for field in ENQUIRY_SCALAR_FIELDS:
                val = request.POST.get(field, '').strip()
                if val:
                    setattr(enquiry, field, val)
            enquiry.save()

            # media
            for doc in request.FILES.getlist('documents'):
                Enquiry_media.objects.create(Enquiry=enquiry, Document=doc)
            for img in request.FILES.getlist('images'):
                Enquiry_media.objects.create(Enquiry=enquiry, Image=img)

            # products — parallel lists posted by the form
            products    = request.POST.getlist('Product')
            field_lists = {f: request.POST.getlist(f) for f in PRODUCT_FIELDS}
            prices      = request.POST.getlist('Target_price')

            for i, product_name in enumerate(products):
                product_name = product_name.strip()
                if not product_name:
                    continue
                product = Enquiry_products(Enquiry=enquiry, Product=product_name)
                for field in PRODUCT_FIELDS:
                    vals = field_lists[field]
                    val  = vals[i].strip() if i < len(vals) else ''
                    if val:
                        setattr(product, field, val)
                raw_price = prices[i].strip() if i < len(prices) else ''
                if raw_price:
                    try:
                        product.Target_price = float(raw_price)
                    except ValueError:
                        pass
                product.save()

        messages.success(request, f'Enquiry saved for "{enquiry.Company_name}".')
        return redirect('enquiry:enquiry_list')

    return _render_add(request)

def _render_add(request):
    return render(request, 'add_enquiry.html', {
        'buyer_list':            buyer_details.objects.only(
                                     'id', 'Company_name', 'Contact_person'
                                 ).order_by('Company_name'),
        'category_list':         _category_list,
        'today':                 timezone.localdate(),
    })

def related_sellers(request, en_id):
    """
    For an enquiry, find:
    1. Direct sellers — suppliers who sell the exact products in the enquiry.
    2. Indirect/upstream sellers — suppliers who sell raw materials that are
       inputs to the enquired products (via DGFT SION recipe data).
    """
    enquiry  = get_object_or_404(Enquiry_details, id=en_id)
    products = Enquiry_products.objects.filter(Enquiry=enquiry).exclude(Product='')

    enquired_names = [p.Product.strip() for p in products if p.Product.strip()]

    direct_qs = Sell_products.objects.filter(
        Product__in=enquired_names
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

    mask         = df['Output Item'].isin(enquired_names)
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
        raw_material_names = list(input_to_outputs.keys())

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
            outputs = [str(o) for o in input_to_outputs.get(sp.Product.strip(), [])]
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
        'enquiry':          enquiry,
        'direct_sellers':   direct_sellers,
        'indirect_sellers': indirect_sellers,
    })