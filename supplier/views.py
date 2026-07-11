from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
import pandas as pd
from supplier.models import supplier_details, supplier_contact_details,supplier_addresses, supplier_media, Sell_products
from django.db.models import Q
from django.utils import timezone
import os, json
from django.conf import settings

SUPPLIER_FIELDS = [
    'Description', 'Website_link', 'GST_number', 'IEC_code',
    'PAN_number', 'DIN_number', 'CIN_number', 'DUNS_number',
    'Contact_person', 'WCPD_code', 'Admin_remark',
]

PRODUCT_FIELDS = [
    'Sector', 'Division', 'Product_group', 'Product_category',
    'HSN_code', 'Factory_address', 'Warehouse_address', 'Min_order_quantity',
]

ADDRESS_FIELDS = ['Address', 'City', 'State', 'Country']

def _import_excel(file_obj):
    """
    Parse and import a supplier excel file.
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

                supplier, was_created = supplier_details.objects.get_or_create(
                    Company_name=company_name,
                    defaults={'Created_at': timezone.localdate()}
                )
                if not was_created:
                    skipped += 1
                    continue

                # scalar company-level fields
                for field in SUPPLIER_FIELDS:
                    if field in group.columns and pd.notna(row[field]):
                        setattr(supplier, field, str(row[field]).strip())
                supplier.save()

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
                                supplier_contact_details.objects.create(
                                    Supplier=supplier, **{kwarg: val}
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

                    supplier_addresses.objects.create(
                        Supplier=supplier,
                        Address=addr_val,
                        City=_get('City'),
                        State=_get('State'),
                        Country=_get('Country'),
                    )

                # products — one row per product (company can span multiple rows for products)
                for _, data in group.iterrows():
                    if 'Product' not in group.columns or pd.isna(data.get('Product')):
                        continue
                    product = Sell_products.objects.create(
                        Supplier=supplier,
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


def suppliers_list(request):
    if request.method == 'POST' and request.FILES.get('supplier_excel'):
        created, skipped, errors = _import_excel(request.FILES['supplier_excel'])
        if errors:
            messages.error(request, f"Import finished with errors: {'; '.join(errors)}")
        else:
            messages.success(request, f"Imported {created} supplier(s). {skipped} already existed and were skipped.")
        return redirect('supplier:suppliers_list')

    suppliers = supplier_details.objects.prefetch_related(
        'Sell_products', 'supplier_contact_details', 'supplier_addresses'
    ).order_by('-Created_at')

    search = request.GET.get('search', '').strip()
    Product_group = request.GET.get('Product_group', '').strip()
    # city   = request.GET.get('city', '').strip()
    # state  = request.GET.get('state', '').strip()
    country = request.GET.get('country', '').strip()

    if search:
        suppliers = suppliers.filter(
            Q(Company_name__icontains=search) |
            Q(Sell_products__Product__icontains=search)
        )

    if Product_group:
        suppliers = suppliers.filter(Sell_products__Product_group=Product_group)

    # if city:
    #     suppliers = suppliers.filter(supplier_addresses__City__icontains=city)

    # if state:
    #     suppliers = suppliers.filter(supplier_addresses__State__icontains=state)

    if country:
        suppliers = suppliers.filter(supplier_addresses__Country__icontains=country)

    # always call distinct() at the end — any filter across a FK relation can produce duplicates
    suppliers = suppliers.distinct()

    context = {
        'search': search, 
        'country': country, #'city': city, 'state': state,
        'Product_group': Product_group,
        'suppliers': suppliers,

    }
    return render(request, 'suppliers_list.html', context)

def delete_supplier(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        sp_id = data.get('sp_id')

        supplier = supplier_details.objects.filter(id=sp_id).first()

        if supplier:
            supplier.delete()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False})