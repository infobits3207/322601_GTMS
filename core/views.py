from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
import pandas as pd
from django.utils import timezone
from datetime import timedelta
import os
from django.conf import settings
from django.views.decorators.http import require_POST

from core.utils import send_notification_email
from buyer.models import Buyer_email_messages, buyer_details
from supplier.models import supplier_details, supplier_email_messages
from enquiry.models import Enquiry_details

def dashboard(request):
    
    return render(request,'dashboard.html',{
        'today'            : timezone.localdate(),
        'Total_buyers'     : buyer_details.objects.all().count(),
        'Total_suppliers'  : supplier_details.objects.all().count(),
        'Total_enquiries'  : Enquiry_details.objects.all().count(),
        'Active_enquiries' : Enquiry_details.objects.filter(Closing_date__gt=timezone.localdate()).count(),
        'Closing_today'    : Enquiry_details.objects.filter(Closing_date=timezone.localdate()).count(),

        'closing_this_week': Enquiry_details.objects.filter(Closing_date__gte = timezone.localdate(),Closing_date__lt = (timezone.localdate()+timedelta(days=7))),
        'new_enquirires'   : Enquiry_details.objects.order_by('-Enquiry_date')[:5],
        'new_buyers'       : buyer_details.objects.order_by('-Created_at')[:5],
        'new_suppliers'    : supplier_details.objects.order_by('-Created_at')[:5],
    })

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
    from_email_key   = request.POST.get('from_email','').strip()

    account = settings.EMAIL_ACCOUNTS.get(from_email_key)

    if not from_email_key:
        return JsonResponse({'success': False, 'error': 'Please select sender(from) email id'})
    
    if not to_email or not subject or not content:
        return JsonResponse({'success': False, 'error': 'To, subject and message are all required.'})

    # send the email
    sent = send_notification_email(to_email, subject, content, account)
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