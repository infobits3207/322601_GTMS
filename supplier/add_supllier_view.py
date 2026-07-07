from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
import pandas as pd
from supplier.models import supplier_details, supplier_contact_details,supplier_addresses, supplier_media, Sell_products
from django.utils import timezone
import os
from django.conf import settings

SUPPLIER_FIELDS = [
    'Description', 'Website_link', 'GST_number', 'IEC_code',
    'PAN_number', 'DIN_number', 'CIN_number', 'DUNS_number',
    'Contact_person', 'WCPD_code', 'Admin_remark',
]

recipe_df = pd.read_excel(
    os.path.join(settings.STATICFILES_DIRS[0], 'recipe_pairs_all_categories.xlsx')
)

def supplier_add(request):
    category_list = recipe_df['Category'].unique().tolist()

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
        'category_list': category_list,
    }

    return render(request, 'supplier_add.html',context)

def fetch_products(request):
    category = request.GET.get('category_name')
    print(category)

    df = recipe_df[recipe_df['Category'] == category]
    print(df.head())

    # The correct way to get unique values across both columns combined
    Product_list = pd.unique(df[['Output Item', 'Input Item']].values.ravel())

    print(Product_list)
    return JsonResponse(list(Product_list),safe=False)