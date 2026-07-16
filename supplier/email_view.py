from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
import json
from django.conf import settings

from supplier.models import supplier_details, supplier_email_messages, supplier_contact_details
from core.utils import send_notification_email   # your existing helper

def email_history(request, sp_id):
    supplier = get_object_or_404(supplier_details, id=sp_id)

    # parse stored emails back into structured dicts
    # stored format: "To: email@x.com\nSubject: ...\n\nbody text"
    email_history = supplier_email_messages.objects.filter(Supplier=supplier).order_by('-Time')

    emails = supplier_contact_details.objects.filter(
        Supplier=supplier
    ).exclude(Email='').values_list('Email', flat=True)

    context = {
        'supplier':      supplier,
        'email_history': email_history,
        'emails':        emails,
    }
    return render(request, 'email_history.html', context)

@require_POST
def send_bulk_email(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request.'})

    from_email = data.get('from','').strip()
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
        c.Email: c.Supplier
        for c in supplier_contact_details.objects.filter(
            Email__in=emails
        ).select_related('Supplier')
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
            # save to history if we can trace this email back to a supplier
            supplier = contact_map.get(email)
            if supplier:
                supplier_email_messages.objects.create(
                    Supplier = supplier,
                    From = account['EMAIL_HOST_USER'],
                    To       = email,
                    Subject  = subject,
                    Body     = body,
                    Time     = now,
                )
        else:
            failed += 1

    return JsonResponse({'success': True, 'sent': sent, 'failed': failed})