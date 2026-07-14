from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from buyer.models import buyer_details
from enquiry.models import Enquiry_details, Enquiry_products, Enquiry_media
from supplier.models import Sell_products
import pandas as pd, os
from django.conf import settings

# ── load recipe data once ──
_recipe_df     = pd.read_excel(os.path.join(settings.STATICFILES_DIRS[0], 'recipe_pairs_all_categories.xlsx'))
_category_list = sorted(_recipe_df['Category'].dropna().unique().tolist())

PRODUCT_FIELDS_RECON = [
    'Sector', 'Division', 'Product_group', 'Product_category',
    'HSN_code', 'Quantity', 'Packaging', 'Currency',
    'Billing_address', 'Delivery_address',
]

ENQUIRY_TYPE_CHOICES = [
    'New requirement', 'Repeat order', 'Price enquiry', 'Sample request', 'Other'
]

def _reconcile_products(enquiry, submitted):
    """
    submitted = list of dicts with product fields.
    Reconcile by Product name as identity key.
    """
    existing     = Enquiry_products.objects.filter(Enquiry=enquiry)
    existing_map = {p.Product.strip(): p for p in existing}
    submitted_keys = set()

    for data in submitted:
        name = data.get('Product', '').strip()
        if not name:
            continue
        submitted_keys.add(name)
        obj = existing_map.get(name) or Enquiry_products(Enquiry=enquiry, Product=name)
        for field in PRODUCT_FIELDS_RECON:
            setattr(obj, field, data.get(field, '').strip())
        raw_price = data.get('Target_price', '').strip()
        if raw_price:
            try:
                obj.Target_price = float(raw_price)
            except ValueError:
                obj.Target_price = None
        else:
            obj.Target_price = None
        obj.save()

    for name, obj in existing_map.items():
        if name not in submitted_keys:
            obj.delete()


def edit_enquiry(request, en_id):
    enquiry  = get_object_or_404(Enquiry_details, id=en_id)
    products = Enquiry_products.objects.filter(Enquiry=enquiry)
    media    = Enquiry_media.objects.filter(Enquiry=enquiry)

    if request.method == 'POST':
        mode = request.POST.get('buyer_mode', 'existing')

        with transaction.atomic():
            if mode == 'existing':
                buyer_id = request.POST.get('buyer_id', '').strip()
                if buyer_id:
                    buyer = get_object_or_404(buyer_details, id=buyer_id)
                    enquiry.buyer        = buyer
                    enquiry.Company_name = buyer.Company_name
            else:
                company_name = request.POST.get('Company_name', '').strip()
                if not company_name:
                    messages.error(request, 'Company name is required.')
                    return _render_edit(request, enquiry, products, media)
                enquiry.buyer        = None
                enquiry.Company_name = company_name
            
            enquiry.Description  = request.POST.get('Description', '').strip()
            enquiry.Enquiry_date = request.POST.get('Enquiry_date') or None
            enquiry.Closing_date = request.POST.get('Closing_date') or None
            enquiry.Enquiry_type = request.POST.get('Enquiry_type', '').strip()
            enquiry.Admin_remark = request.POST.get('Admin_remark', '').strip()
            enquiry.save()

            # reconcile products
            raw_products = request.POST.getlist('Product')
            field_lists  = {f: request.POST.getlist(f) for f in PRODUCT_FIELDS_RECON}
            prices       = request.POST.getlist('Target_price')
            submitted = []
            for i, pname in enumerate(raw_products):
                if not pname.strip():
                    continue
                d = {'Product': pname.strip(), 'Target_price': prices[i] if i < len(prices) else ''}
                for field in PRODUCT_FIELDS_RECON:
                    vals = field_lists[field]
                    d[field] = vals[i] if i < len(vals) else ''
                submitted.append(d)
            _reconcile_products(enquiry, submitted)

            # new media
            for doc in request.FILES.getlist('documents'):
                Enquiry_media.objects.create(Enquiry=enquiry, Document=doc)
            for img in request.FILES.getlist('images'):
                Enquiry_media.objects.create(Enquiry=enquiry, Image=img)

            # delete marked media
            for mid in request.POST.getlist('delete_media'):
                Enquiry_media.objects.filter(id=mid, Enquiry=enquiry).delete()

        messages.success(request, 'Enquiry updated successfully.')
        return redirect('enquiry:edit_enquiry',en_id)

    return _render_edit(request, enquiry, products, media)


def _render_edit(request, enquiry, products, media):
    return render(request, 'edit_enquiry.html', {
        'enquiry':              enquiry,
        'products':             products,
        'documents':            media.exclude(Document='').exclude(Document=None),
        'images':               media.exclude(Image='').exclude(Image=None),
        'buyer_list':           buyer_details.objects.only('id', 'Company_name', 'Contact_person').order_by('Company_name'),
        'category_list':        _category_list,
        'enquiry_type_choices': ENQUIRY_TYPE_CHOICES,
    })