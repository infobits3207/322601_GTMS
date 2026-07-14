from buyer.models import Buyer_contact_details, Buyer_email_messages
from core.utils import send_notification_email

from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

@require_POST
def send_bulk_email(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request.'})

    emails  = data.get('emails', [])
    subject = data.get('subject', '').strip()
    body    = data.get('body', '').strip()

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

        ok = send_notification_email(email, subject, body)
        if ok:
            sent += 1
            # save to history if we can trace this email back to a buyer
            buyer = contact_map.get(email)
            if buyer:
                Buyer_email_messages.objects.create(
                    Buyer = buyer,
                    To       = email,
                    Subject  = subject,
                    Body     = body,
                    Time     = now,
                )
        else:
            failed += 1

    return JsonResponse({'success': True, 'sent': sent, 'failed': failed})