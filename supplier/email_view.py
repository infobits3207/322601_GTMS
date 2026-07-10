from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
import json

from supplier.models import supplier_details, supplier_email_messages, supplier_contact_details
from buyer.models import Buyer_email_messages, buyer_details
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

    # build a lookup: email -> supplier
    # one query instead of hitting the DB inside the loop
    from supplier.models import supplier_contact_details
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

        ok = send_notification_email(email, subject, body)
        if ok:
            sent += 1
            # save to history if we can trace this email back to a supplier
            supplier = contact_map.get(email)
            if supplier:
                supplier_email_messages.objects.create(
                    Supplier = supplier,
                    To       = email,
                    Subject  = subject,
                    Body     = body,
                    Time     = now,
                )
        else:
            failed += 1

    return JsonResponse({'success': True, 'sent': sent, 'failed': failed})