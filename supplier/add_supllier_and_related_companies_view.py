from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
import pandas as pd
from supplier.models import supplier_details, supplier_contact_details, supplier_addresses, supplier_media, Sell_products
from buyer.models import Purchase_products
from django.utils import timezone
import os
from django.conf import settings


SUPPLIER_FIELDS = [
    'Description', 'Website_link', 'GST_number', 'IEC_code',
    'PAN_number', 'DIN_number', 'CIN_number', 'DUNS_number',
    'Contact_person', 'WCPD_code', 'Admin_remark',
]

_recipe_df = pd.read_excel(
    os.path.join(settings.STATICFILES_DIRS[0], 'recipe_pairs_all_categories.xlsx')
)
_category_list = sorted(_recipe_df['Category'].dropna().unique().tolist())

def supplier_add(request):

    if request.method == 'POST':
        company_name = request.POST.get('Company_name', '').strip()
        if not company_name:
            messages.error(request, 'Company name is required.')
            return render(request, 'suppliers/supplier_add.html')

        with transaction.atomic():
            supplier = supplier_details.objects.create(
                Company_name=company_name,
                Created_at=timezone.localdate(),
            )

            # scalar fields
            for field in SUPPLIER_FIELDS:
                val = request.POST.get(field, '').strip()
                if val:
                    setattr(supplier, field, val)
            supplier.save()

            # contacts
            for email in request.POST.getlist('Email'):
                if email.strip():
                    supplier_contact_details.objects.create(Supplier=supplier, Email=email.strip())
            for phone in request.POST.getlist('Phone'):
                if phone.strip():
                    supplier_contact_details.objects.create(Supplier=supplier, Phone=phone.strip())
            for fax in request.POST.getlist('FAX'):
                if fax.strip():
                    supplier_contact_details.objects.create(Supplier=supplier, FAX=fax.strip())

            products = request.POST.getlist('Product')
            sectors = request.POST.getlist('Sector')
            divisions = request.POST.getlist('Division')
            product_groups = request.POST.getlist('Product_group')
            product_categories = request.POST.getlist('Product_category')
            HSN_code = request.POST.getlist('HSN_code')
            min_order_quantities = request.POST.getlist('Min_order_quantity')
            factory_addresses = request.POST.getlist('Factory_address')
            warehouse_addresses = request.POST.getlist('Warehouse_address')

            for i, prd in enumerate(products):
                if prd.strip():
                    Sell_products.objects.create(
                        Supplier = supplier,
                        Sector = sectors[i].strip() if i < len(sectors) else '',
                        Division = divisions[i].strip() if i < len(divisions) else '',
                        Product_group = product_groups[i].strip() if i < len(product_groups) else '',
                        Product_category = product_categories[i].strip() if i < len(product_categories) else '',
                        Product = prd.strip(),
                        HSN_code = HSN_code[i].strip() if i < len(HSN_code) else '',
                        Factory_address = factory_addresses[i].strip() if i < len(factory_addresses) else '',
                        Warehouse_address = warehouse_addresses[i].strip() if i < len(warehouse_addresses) else '',
                        Min_order_quantity = min_order_quantities[i].strip() if i < len(min_order_quantities) else '',
                    )

            # addresses — form posts parallel lists: Address[], City[], State[], Country[]
            addresses   = request.POST.getlist('Address')
            cities      = request.POST.getlist('City')
            states      = request.POST.getlist('State')
            countries   = request.POST.getlist('Country')
            for i, addr in enumerate(addresses):
                if addr.strip():
                    supplier_addresses.objects.create(
                        Supplier=supplier,
                        Address=addr.strip(),
                        City=cities[i].strip()    if i < len(cities)    else '',
                        State=states[i].strip()   if i < len(states)    else '',
                        Country=countries[i].strip() if i < len(countries) else '',
                    )

            # documents & images
            for doc in request.FILES.getlist('documents'):
                supplier_media.objects.create(Supplier=supplier, Document=doc)
            for img in request.FILES.getlist('images'):
                supplier_media.objects.create(Supplier=supplier, Image=img)

        messages.success(request, f'Supplier "{company_name}" added successfully.')
        return redirect('supplier:suppliers_list')
    
    context = {
        'category_list': _category_list,
        'product_group_choices': ['FCSL','ICSL','FCCL','ICCL','FCSC','ICSC','DCSC','DCSL'],
    }

    return render(request, 'supplier_add.html',context)

def fetch_products(request):
    category = request.GET.get('category_name')
    print(category)

    df = _recipe_df[_recipe_df['Category'] == category]
    print(df.head())

    # The correct way to get unique values across both columns combined
    Product_list = pd.unique(df[['Output Item', 'Input Item']].values.ravel())

    print(Product_list)
    return JsonResponse(list(Product_list),safe=False)


def _related_suppliers(supplier_products):
    sell_names = [p.Product.strip().upper() for p in supplier_products if p.Product.strip()]
    if not sell_names or _recipe_df.empty:
        return []

    recipe = _recipe_df.copy()
    recipe['Input Item Norm'] = recipe['Input Item'].str.strip().str.upper()
    recipe['Output Item Norm'] = recipe['Output Item'].str.strip().str.upper()

    mask = recipe['Input Item Norm'].isin(sell_names)
    output_items = recipe[mask][['Output Item', 'Output Item Norm', 'Input Item']].drop_duplicates()

    if output_items.empty:
        return []

    output_names = output_items['Output Item'].unique().tolist()  # original casing for the DB query

    seller_products = Sell_products.objects.filter(
        Product__in=output_names
    ).select_related('Supplier')

    results = []
    seen = set()
    for sp in seller_products:
        product_norm = sp.Product.strip().upper()
        key = (sp.Supplier.id, product_norm)
        if key in seen:
            continue
        seen.add(key)

        # exact, case-insensitive match
        matching = output_items[output_items['Output Item Norm'] == product_norm]
        via = matching['Input Item'].tolist()

        results.append({
            'Supplier': sp.Supplier,
            'needs_product': sp.Product,
            'via_supplier_product': via,
        })

    return results

def _related_buyers_direct(supplier_products):
    """
    Also find buyers who directly purchase the same product the supplier sells.
    """
    sell_names = [p.Product.strip() for p in supplier_products if p.Product.strip()]
    if not sell_names:
        return []
    buyer_products = Purchase_products.objects.filter(
        Product__in=sell_names
    ).select_related('Buyer').distinct()
    return list(buyer_products)

def related_companies(request,sp_id):
    supplier = get_object_or_404(supplier_details, id=sp_id)
    contacts  = supplier_contact_details.objects.filter(Supplier=supplier)
    addresses = supplier_addresses.objects.filter(Supplier=supplier)
    media     = supplier_media.objects.filter(Supplier=supplier)
    products  = Sell_products.objects.filter(Supplier=supplier).exclude(Product='')

    related_suppliers = _related_suppliers(products)
    related_buyers_direct   = _related_buyers_direct(products)

    context = {
        'supplier':     supplier,
        'Emails':       contacts.exclude(Email='').values_list('Email', flat=True),
        'Phone_numbers':contacts.exclude(Phone='').values_list('Phone', flat=True),
        'FAX_numbers':  contacts.exclude(FAX='').values_list('FAX', flat=True),
        'addresses':    addresses,
        'media':        media,
        'documents':    media.exclude(Document='').exclude(Document=None),
        'images':       media.exclude(Image='').exclude(Image=None),
        'Products':     products,
        'related_buyers_direct':   related_buyers_direct,
        'related_suppliers': related_suppliers,
        'category_list': _category_list,
    }
    return render(request,'related_companies.html',context)