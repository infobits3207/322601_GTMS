from django.shortcuts import render, get_object_or_404
from core.utils import send_notification_email
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.conf import settings

from buyer.models import buyer_details, Buyer_contact_details, Buyer_email_messages

@require_POST
def send_bulk_email(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request.'})

    from_email = data.get('from',[])
    emails  = data.get('emails', [])
    subject = data.get('subject', '').strip()
    body    = data.get('body', '').strip()

    account = settings.EMAIL_ACCOUNTS.get(from_email)

    if not from_email:
        return JsonResponse({'success': False, 'error': 'Sender(from) id is required.'})
    if not emails:
        return JsonResponse({'success': False, 'error': 'No recipients provided.'})
    if not subject:
        return JsonResponse({'success': False, 'error': 'Subject is required.'})
    if not body:
        return JsonResponse({'success': False, 'error': 'Message body is required.'})

    contact_map = {
        c.Email: c.Buyer
        for c in Buyer_contact_details.objects.filter(
            Email__in=emails
        ).select_related('Buyer')
        if c.Email
    }

    sent   = 0
    failed = 0
    now    = timezone.now()

    for email in emails:
        email = email.strip()
        if not email:
            continue
        
        ok = send_notification_email(email, subject, body, account)
        if ok:
            sent += 1
            # save to history if we can trace this email back to a buyer
            buyer = contact_map.get(email)
            if buyer:
                Buyer_email_messages.objects.create(
                    Buyer = buyer,
                    From = account['EMAIL_HOST_USER'],
                    To       = email,
                    Subject  = subject,
                    Body     = body,
                    Time     = now,
                )
        else:
            failed += 1

    return JsonResponse({'success': True, 'sent': sent, 'failed': failed})

def email_history(request, bu_id):
    buyer = get_object_or_404(buyer_details, id=bu_id)

    # parse stored emails back into structured dicts
    # stored format: "To: email@x.com\nSubject: ...\n\nbody text"
    email_history = Buyer_email_messages.objects.filter(Buyer=buyer).order_by('-Time')

    emails = Buyer_contact_details.objects.filter(Buyer=buyer
        ).exclude(Email='').values_list('Email', flat=True)

    context = {
        'buyer':          buyer,
        'email_history':  email_history,
        'emails':         emails,
    }
    return render(request, 'email_history.html', context)