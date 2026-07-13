from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.conf import settings
from supplier.models import (
    supplier_details, supplier_contact_details,
    supplier_addresses, supplier_media, Sell_products
)
import pandas as pd
import os

# ── load recipe data once at startup ──
_recipe_df = pd.read_excel(
    os.path.join(settings.STATICFILES_DIRS[0], 'recipe_pairs_all_categories.xlsx')
)
_category_list = sorted(_recipe_df['Category'].dropna().unique().tolist())

SUPPLIER_FIELDS = [
    'Company_name', 'Description', 'Website_link', 'GST_number',
    'IEC_code', 'PAN_number', 'DIN_number', 'CIN_number',
    'DUNS_number', 'Contact_person', 'WCPD_code', 'Admin_remark',
]

PRODUCT_FIELDS = [
    'Sector', 'Division', 'Product_group', 'Product_category',
    'HSN_code', 'Factory_address', 'Warehouse_address', 'Min_order_quantity',
]

ADDRESS_FIELDS = ['Address', 'City', 'State', 'Country']

# ── helpers ───────────────────────────────────────────────

def _reconcile_contacts(supplier, field, new_values):
    new_set = {v.strip() for v in new_values if v.strip()}
    existing_qs = supplier_contact_details.objects.filter(Supplier=supplier)
    existing_set = set(existing_qs.exclude(**{field: ''}).values_list(field, flat=True))
    for val in new_set - existing_set:
        supplier_contact_details.objects.create(Supplier=supplier, **{field: val})
    to_delete = existing_set - new_set
    if to_delete:
        existing_qs.filter(**{f'{field}__in': to_delete}).delete()


def _reconcile_addresses(supplier, submitted):
    """
    submitted = list of dicts [{'Address':..,'City':..,'State':..,'Country':..}, ...]
    Reconcile by Address text as identity key.
    """
    existing = supplier_addresses.objects.filter(Supplier=supplier)
    existing_map = {a.Address.strip(): a for a in existing}
    submitted_keys = set()

    for data in submitted:
        addr = data.get('Address', '').strip()
        if not addr:
            continue
        submitted_keys.add(addr)
        if addr in existing_map:
            # update city/state/country in case they changed
            obj = existing_map[addr]
            obj.City    = data.get('City', '').strip()
            obj.State   = data.get('State', '').strip()
            obj.Country = data.get('Country', '').strip()
            obj.save()
        else:
            supplier_addresses.objects.create(
                Supplier=supplier,
                Address=addr,
                City=data.get('City', '').strip(),
                State=data.get('State', '').strip(),
                Country=data.get('Country', '').strip(),
            )

    # delete addresses that were removed in the form
    for addr_text, obj in existing_map.items():
        if addr_text not in submitted_keys:
            obj.delete()


def _reconcile_products(supplier, submitted):
    """
    submitted = list of dicts with product fields.
    Reconcile by Product name as identity key.
    """
    existing = Sell_products.objects.filter(Supplier=supplier)
    existing_map = {p.Product.strip(): p for p in existing}
    submitted_keys = set()

    for data in submitted:
        product_name = data.get('Product', '').strip()
        if not product_name:
            continue
        submitted_keys.add(product_name)
        if product_name in existing_map:
            obj = existing_map[product_name]
        else:
            obj = Sell_products(Supplier=supplier, Product=product_name)
        for field in PRODUCT_FIELDS:
            setattr(obj, field, data.get(field, '').strip())
        obj.save()

    for name, obj in existing_map.items():
        if name not in submitted_keys:
            obj.delete()

# ── views ─────────────────────────────────────────────────

def supplier_detail(request, sp_id):
    supplier = get_object_or_404(supplier_details, id=sp_id)
    contacts  = supplier_contact_details.objects.filter(Supplier=supplier)
    addresses = supplier_addresses.objects.filter(Supplier=supplier)
    media     = supplier_media.objects.filter(Supplier=supplier)
    products  = Sell_products.objects.filter(Supplier=supplier).exclude(Product='')

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
        'category_list': _category_list,
    }
    return render(request, 'Edit_supplier.html', context)


def edit_supplier(request, sp_id):
    supplier = get_object_or_404(supplier_details, id=sp_id)

    if request.method == 'POST':
        with transaction.atomic():

            # scalar fields
            for field in SUPPLIER_FIELDS:
                val = request.POST.get(field, '').strip()
                setattr(supplier, field, val)
            supplier.save()

            # contacts
            _reconcile_contacts(supplier, 'Email', request.POST.getlist('Email'))
            _reconcile_contacts(supplier, 'Phone', request.POST.getlist('Phone'))
            _reconcile_contacts(supplier, 'FAX',   request.POST.getlist('FAX'))

            # addresses — form posts parallel lists
            raw_addresses = request.POST.getlist('Address')
            raw_cities    = request.POST.getlist('City')
            raw_states    = request.POST.getlist('State')
            raw_countries = request.POST.getlist('Country')
            submitted_addresses = [
                {
                    'Address': raw_addresses[i],
                    'City':    raw_cities[i]    if i < len(raw_cities)    else '',
                    'State':   raw_states[i]    if i < len(raw_states)    else '',
                    'Country': raw_countries[i] if i < len(raw_countries) else '',
                }
                for i in range(len(raw_addresses))
            ]
            _reconcile_addresses(supplier, submitted_addresses)

            # products — form posts parallel lists
            raw_products = request.POST.getlist('Product')
            submitted_products = []
            field_lists = {f: request.POST.getlist(f) for f in PRODUCT_FIELDS}
            for i, product_name in enumerate(raw_products):
                if not product_name.strip():
                    continue
                data = {'Product': product_name}
                for field in PRODUCT_FIELDS:
                    vals = field_lists[field]
                    data[field] = vals[i] if i < len(vals) else ''
                submitted_products.append(data)
            _reconcile_products(supplier, submitted_products)

            # new media files (existing ones are kept, only new ones added)
            for doc in request.FILES.getlist('documents'):
                supplier_media.objects.create(Supplier=supplier, Document=doc)
            for img in request.FILES.getlist('images'):
                supplier_media.objects.create(Supplier=supplier, Image=img)

            # delete media if requested
            for media_id in request.POST.getlist('delete_media'):
                supplier_media.objects.filter(id=media_id, Supplier=supplier).delete()

        messages.success(request, 'Supplier updated successfully.')
        return redirect('supplier:supplier_detail', sp_id)

    return redirect('supplier:supplier_detail', sp_id)