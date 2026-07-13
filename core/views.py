from django.shortcuts import render
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
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
import json

from supplier.models import supplier_details, supplier_email_messages, supplier_contact_details
from buyer.models import Buyer_email_messages, buyer_details
from core.utils import send_notification_email   # your existing helper

def dashboard(request):
    return render(request,'dashboard.html')

_recipe_df = pd.read_excel(
    os.path.join(settings.STATICFILES_DIRS[0], 'recipe_pairs_all_categories.xlsx')
)

def fetch_products(request):
    category = request.GET.get('category_name')
    print(category)

    df = _recipe_df[_recipe_df['Category'] == category]
    print(df.head())

    # The correct way to get unique values across both columns combined
    Product_list = pd.unique(df[['Output Item', 'Input Item']].values.ravel())

    print(Product_list)
    return JsonResponse(list(Product_list),safe=False)

@require_POST
def send_company_email(request):
    to_email     = request.POST.get('to_email', '').strip()
    subject      = request.POST.get('subject', '').strip()
    content      = request.POST.get('content', '').strip()
    company_type = request.POST.get('company_type', '')
    company_id   = request.POST.get('company_id', '')

    if not to_email or not subject or not content:
        return JsonResponse({'success': False, 'error': 'To, subject and message are all required.'})

    # send the email
    sent = send_notification_email(to_email, subject, content)
    if not sent:
        return JsonResponse({'success': False, 'error': 'Email could not be sent. Check server logs.'})

    # save to email history
    try:
        if company_type == 'buyer':
            buyer = get_object_or_404(buyer_details, id=company_id)
            Buyer_email_messages.objects.create(
                Buyer=buyer,
                To = to_email,
                Subject = subject,
                Body = content,
                Time=timezone.now(),
            )
        elif company_type == 'supplier':
            supplier = get_object_or_404(supplier_details, id=company_id)
            supplier_email_messages.objects.create(
                Supplier=supplier,
                To = to_email,
                Subject = subject,
                Body = content,
                Time=timezone.now(),
            )
    except Exception as e:
        # email was sent — don't fail the response just because history save failed
        print(f"Email history save error: {e}")

    return JsonResponse({'success': True})