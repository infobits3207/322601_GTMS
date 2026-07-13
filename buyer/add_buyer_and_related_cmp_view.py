from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
import pandas as pd
from buyer.models import buyer_details, Buyer_contact_details, Buyer_addresses, Buyer_media, Purchase_products
from buyer.models import Purchase_products
from django.utils import timezone
import os
from django.conf import settings

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
    print(">>>>>>>>>>>>>>>")
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
    print(context['category_list'])
    return render(request, 'add_buyer.html',context)