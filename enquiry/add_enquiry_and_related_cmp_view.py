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
                product = Enquiry_products(Supplier=enquiry, Product=product_name)
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