from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from buyer.models import buyer_details
from enquiry.models import Enquiry_details, Enquiry_products
import pandas as pd, os
from django.conf import settings

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

def _import_excel(file_obj):
    """
    Excel format (same pattern as supplier import):
      - One row per product.
      - Company-level fields (Company_name, Enquiry_type, etc.) filled
        only on the FIRST row for that company; subsequent rows left blank.
      - Multiple products for one company = multiple rows sharing Company_name.

    Optional columns:
      Company_name*, Enquiry_date, Closing_date, Enquiry_type, Admin_remark,
      Description, Product*, Sector, Division, Product_group, Product_category,
      HSN_code, Quantity, Packaging, Target_price, Currency,
      Billing_address, Delivery_address
    """
    df = pd.read_excel(file_obj)
    df = df.dropna(subset=['Company_name'])
    grouped = df.groupby('Company_name')

    created, skipped, errors = 0, 0, []

    for company_name, group in grouped:
        try:
            with transaction.atomic():
                row = group.iloc[0]

                enquiry, was_created = Enquiry_details.objects.get_or_create(
                    Company_name=company_name,
                    defaults={'Enquiry_date': timezone.localdate()}
                )
                if not was_created:
                    skipped += 1
                    continue

                # company-level scalar fields
                for field in EXCEL_COMPANY_FIELDS:
                    if field in group.columns and pd.notna(row.get(field)):
                        setattr(enquiry, field, str(row[field]).strip())

                for date_field in ('Enquiry_date', 'Closing_date'):
                    if date_field in group.columns and pd.notna(row.get(date_field)):
                        try:
                            setattr(enquiry, date_field, pd.to_datetime(row[date_field]).date())
                        except Exception:
                            pass

                # auto-link to existing buyer by name
                buyer = buyer_details.objects.filter(Company_name=company_name).first()
                if buyer:
                    enquiry.buyer = buyer
                enquiry.save()

                # products — one row per product
                for _, data in group.iterrows():
                    product_name = str(data.get('Product', '')).strip() if pd.notna(data.get('Product')) else ''
                    if not product_name:
                        continue

                    product = Enquiry_products(Enquiry=enquiry, Product=product_name)
                    for field in PRODUCT_FIELDS:
                        if field in group.columns and pd.notna(data.get(field)):
                            setattr(product, field, str(data[field]).strip())
                    if 'Target_price' in group.columns and pd.notna(data.get('Target_price')):
                        try:
                            product.Target_price = float(data['Target_price'])
                        except ValueError:
                            pass
                    product.save()

                created += 1

        except Exception as e:
            errors.append(f"{company_name}: {e}")

    return created, skipped, errors


# ── views ─────────────────────────────────────────────────

def enquiry_list(request):
    if request.method == 'POST' and request.FILES.get('enquiry_excel'):
        created, skipped, errors = _import_excel(request.FILES['enquiry_excel'])
        if errors:
            messages.error(request, f"Import finished with errors: {'; '.join(errors)}")
        else:
            messages.success(
                request,
                f"Imported {created} enquiry(s). {skipped} already existed and were skipped."
            )
        return redirect('enquiry:enquiry_list')

    enquiries = Enquiry_details.objects.prefetch_related('Enquiry_products').select_related('buyer')
    
    sort = request.GET.get('sort', 'asc')
    if sort == 'asc':
        enquiries = enquiries.order_by('Closing_date')
    else:
        enquiries = enquiries.order_by('-Closing_date')

    search             = request.GET.get('search', '').strip()
    enquiry_date_from  = request.GET.get('enquiry_date_from', '').strip()
    enquiry_date_to    = request.GET.get('enquiry_date_to', '').strip()
    closing_date_from  = request.GET.get('closing_date_from', '').strip()
    closing_date_to    = request.GET.get('closing_date_to', '').strip()

    if search:
        enquiries = enquiries.filter(
            Q(Company_name__icontains=search) |
            Q(buyer__Company_name__icontains=search) |
            Q(Enquiry_products__Product__icontains=search)
        )
    if enquiry_date_from:
        enquiries = enquiries.filter(Enquiry_date__gte=enquiry_date_from)
    if enquiry_date_to:
        enquiries = enquiries.filter(Enquiry_date__lte=enquiry_date_to)
    if closing_date_from:
        enquiries = enquiries.filter(Closing_date__gte=closing_date_from)
    if closing_date_to:
        enquiries = enquiries.filter(Closing_date__lte=closing_date_to)

    enquiries = enquiries.distinct()

    return render(request, 'enquiry_list.html', {
        'enquiries':         enquiries,
        'search':            search,
        'enquiry_date_from': enquiry_date_from,
        'enquiry_date_to':   enquiry_date_to,
        'closing_date_from': closing_date_from,
        'closing_date_to':   closing_date_to,
        'today':             timezone.localdate()
    })