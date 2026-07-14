from django.shortcuts import render, redirect, get_object_or_404
import os,pandas as pd
from django.conf import settings
from django.db import transaction
from django.contrib import messages

from buyer.models import buyer_details, Buyer_addresses, Buyer_contact_details, Purchase_products, Buyer_media

# ── load recipe data once at startup ──
_recipe_df = pd.read_excel(
    os.path.join(settings.STATICFILES_DIRS[0], 'recipe_pairs_all_categories.xlsx')
)
_category_list = sorted(_recipe_df['Category'].dropna().unique().tolist())

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

def _reconcile_contacts(buyer, field, new_values):
    new_set = {v.strip() for v in new_values if v.strip()}

    existing_qs = Buyer_contact_details.objects.filter(Buyer=buyer)
    existing_set = set(existing_qs.exclude(**{field: ''}).values_list(field, flat=True))
    for val in new_set - existing_set:
        Buyer_contact_details.objects.create(Buyer=buyer, **{field: val})
    to_delete = existing_set - new_set
    if to_delete:
        existing_qs.filter(**{f'{field}__in': to_delete}).delete()


def _reconcile_addresses(buyer, submitted):
    """
    submitted = list of dicts [{'Address':..,'City':..,'State':..,'Country':..}, ...]
    Reconcile by Address text as identity key.
    """
    existing = Buyer_addresses.objects.filter(Buyer=buyer)
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
            Buyer_addresses.objects.create(
                Buyer=buyer,
                Address=addr,
                City=data.get('City', '').strip(),
                State=data.get('State', '').strip(),
                Country=data.get('Country', '').strip(),
            )

    # delete addresses that were removed in the form
    for addr_text, obj in existing_map.items():
        if addr_text not in submitted_keys:
            obj.delete()


def _reconcile_products(buyer, submitted):
    """
    submitted = list of dicts with product fields.
    Reconcile by Product name as identity key.
    """
    existing = Purchase_products.objects.filter(Buyer=buyer)
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
            obj = Purchase_products(Buyer=buyer, Product=product_name)
        for field in PRODUCT_FIELDS:
            setattr(obj, field, data.get(field, '').strip())
        obj.save()

    for name, obj in existing_map.items():
        if name not in submitted_keys:
            obj.delete()

def buyer_detail(request,bu_id):
    buyer = get_object_or_404(buyer_details, id=bu_id)
    contacts  = Buyer_contact_details.objects.filter(Buyer=buyer)
    addresses = Buyer_addresses.objects.filter(Buyer=buyer)
    media     = Buyer_media.objects.filter(Buyer=buyer)
    products  = Purchase_products.objects.filter(Buyer=buyer).exclude(Product='')

    context = {
        'buyer':     buyer,
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
    return render(request,'edit_buyer.html', context)


def edit_buyer(request, bu_id):
    buyer = get_object_or_404(buyer_details, id=bu_id)

    if request.method == 'POST':
        with transaction.atomic():

            # scalar fields
            for field in BUYER_FIELDS:
                val = request.POST.get(field, '').strip()
                setattr(buyer, field, val)
            buyer.save()

            # contacts
            _reconcile_contacts(buyer, 'Email', request.POST.getlist('Email'))
            _reconcile_contacts(buyer, 'Phone', request.POST.getlist('Phone'))
            _reconcile_contacts(buyer, 'FAX',   request.POST.getlist('FAX'))

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
            _reconcile_addresses(buyer, submitted_addresses)

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
            _reconcile_products(buyer, submitted_products)

            # new media files (existing ones are kept, only new ones added)
            for doc in request.FILES.getlist('documents'):
                Buyer_media.objects.create(Buyer=buyer, Document=doc)
            for img in request.FILES.getlist('images'):
                Buyer_media.objects.create(Buyer=buyer, Image=img)

            # delete media if requested
            for media_id in request.POST.getlist('delete_media'):
                Buyer_media.objects.filter(id=media_id, Buyer=buyer).delete()

        messages.success(request, 'Buyer updated successfully.')
        return redirect('buyer:buyer_detail', bu_id)

    return redirect('buyer:buyer_detail', bu_id)