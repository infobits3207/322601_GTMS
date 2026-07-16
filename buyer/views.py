from django.shortcuts import render, redirect
from django.db.models import Q
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
import pandas as pd
from django.conf import settings

from buyer.models import buyer_details, Buyer_contact_details, Buyer_addresses, Purchase_products

BUYER_FIELDS = [
    'Company_name', 'Description', 'Website_link', 'GST_number',
    'IEC_code', 'PAN_number', 'DIN_number', 'CIN_number',
    'DUNS_number', 'Contact_person', 'WCPD_code', 'Admin_remark',
    'Payment_terms', 'Supplier_preferences', 'Transport_preferences',
    'Monthly_requirements',
]

PRODUCT_FIELDS = [
    'Sector', 'Division', 'Product_group', 'Product_category',
    'HSN_code', 'Billing_address', 'Delivery_address',
]

ADDRESS_FIELDS = ['Address', 'City', 'State', 'Country']

def _import_excel(file_obj):
    """
    Parse and import a buyer excel file.
    Returns (created_count, skipped_count, errors_list).

    Expected columns (all optional except Company_name):
      Company_name, Description, Website_link, GST_number, IEC_code,
      PAN_number, DIN_number, CIN_number, DUNS_number, Contact_person,
      WCPD_code, Admin_remark,
      Email, Contact_number, FAX,          ← comma-separated per cell
      Address1, City1, State1, Country1,   ← first address
      Address2, City2, State2, Country2,   ← second address  (optional)
      Address3, City3, State3, Country3,   ← third address   (optional)
      ...                                  ← any number of address sets
      Product, Sector, Division, Product_group, Product_category,
      HSN_code, Factory_address, Warehouse_address, Min_order_quantity
    """
    df = pd.read_excel(file_obj)
    df = df.dropna(subset=['Company_name'])
    grouped = df.groupby('Company_name')

    # detect how many address sets exist in this file, e.g. Address1, Address2 ...
    # works regardless of how many the user has added
    address_indices = sorted(set(
        int(col.replace('Address', ''))
        for col in df.columns
        if col.startswith('Address') and col.replace('Address', '').isdigit()
    ))

    created, skipped, errors = 0, 0, []

    for company_name, group in grouped:
        try:
            with transaction.atomic():
                row = group.iloc[0]   # all data is on one row per company

                buyer, was_created = buyer_details.objects.get_or_create(
                    Company_name=company_name,
                    defaults={'Created_at': timezone.localdate()}
                )
                if not was_created:
                    skipped += 1
                    continue

                # scalar company-level fields
                for field in BUYER_FIELDS:
                    if field in group.columns and pd.notna(row[field]):
                        setattr(buyer, field, str(row[field]).strip())
                buyer.save()

                # contacts (comma-separated in one cell)
                for col, kwarg in [
                    ('Email', 'Email'),
                    ('Contact_number', 'Phone'),
                    ('FAX', 'FAX'),
                ]:
                    if col in group.columns and pd.notna(row.get(col)):
                        for val in str(row[col]).split(','):
                            val = val.strip()
                            if val:
                                Buyer_contact_details.objects.create(
                                    Buyer=buyer, **{kwarg: val}
                                )

                # addresses — Address1/City1/State1/Country1, Address2/City2/...
                for i in address_indices:
                    addr_col = f'Address{i}'
                    if addr_col not in group.columns:
                        continue
                    addr_val = str(row[addr_col]).strip() if pd.notna(row.get(addr_col)) else ''
                    if not addr_val:
                        continue  # this address slot is empty for this company, skip

                    def _get(col):
                        c = f'{col}{i}'
                        return str(row[c]).strip() if c in group.columns and pd.notna(row.get(c)) else ''

                    Buyer_addresses.objects.create(
                        Buyer=buyer,
                        Address=addr_val,
                        City=_get('City'),
                        State=_get('State'),
                        Country=_get('Country'),
                    )

                # products — one row per product (company can span multiple rows for products)
                for _, data in group.iterrows():
                    if 'Product' not in group.columns or pd.isna(data.get('Product')):
                        continue
                    product = Purchase_products.objects.create(
                        Buyer=buyer,
                        Product=str(data['Product']).strip()
                    )
                    for field in PRODUCT_FIELDS:
                        if field in group.columns and pd.notna(data.get(field)):
                            setattr(product, field, str(data[field]).strip())
                    product.save()

                created += 1

        except Exception as e:
            errors.append(f"{company_name}: {e}")

    return created, skipped, errors

def buyer_list(request):
    if request.method == 'POST' and request.FILES.get('buyer_excel'):
        created, skipped, errors = _import_excel(request.FILES['buyer_excel'])
        if errors:
            messages.error(request, f"Import finished with errors: {'; '.join(errors)}")
        else:
            messages.success(request, f"Imported {created} buyer(s). {skipped} already existed and were skipped.")
        return redirect('buyer:buyer_list')
    
    buyers = buyer_details.objects.prefetch_related(
        'Buyer_contact_details', 'Purchase_products', 'Buyer_addresses'
    ).order_by('-Created_at')

    search = request.GET.get('search', '').strip()
    Product_group = request.GET.get('Product_group', '').strip()
    country = request.GET.get('country', '').strip()

    if search:
        buyers = buyers.filter(
            Q(Company_name__icontains=search) |
            Q(Purchase_products__Product__icontains=search)
        )

    if Product_group:
        buyers = buyers.filter(Purchase_products__Product_group=Product_group)

    if country:
        buyers = buyers.filter(Buyer_addresses__Country__icontains=country)

    buyers = buyers.distinct()

    context = {
        'search': search, 
        'country': country, #'city': city, 'state': state,
        'Product_group': Product_group,
        'buyers': buyers,
    }
    return render(request, "buyer_list.html", context)