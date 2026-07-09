from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from supplier.models import supplier_details, supplier_email_messages, supplier_contact_details
from buyer.models import Buyer_email_messages, buyer_details
from django.utils import timezone
from core.utils import send_notification_email   # your existing helper
from django.views.decorators.http import require_POST

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
                Email=f"To: {to_email}\nSubject: {subject}\n\n{content}",
                Time=timezone.now(),
            )
        elif company_type == 'supplier':
            supplier = get_object_or_404(supplier_details, id=company_id)
            supplier_email_messages.objects.create(
                Supplier=supplier,
                Email=f"To: {to_email}\nSubject: {subject}\n\n{content}",
                Time=timezone.now(),
            )
    except Exception as e:
        # email was sent — don't fail the response just because history save failed
        print(f"Email history save error: {e}")

    return JsonResponse({'success': True})

def email_history(request, sp_id):
    supplier = get_object_or_404(supplier_details, id=sp_id)

    # parse stored emails back into structured dicts
    # stored format: "To: email@x.com\nSubject: ...\n\nbody text"
    raw_history = supplier_email_messages.objects.filter(
        Supplier=supplier
    ).order_by('-Time')

    email_history = []
    for record in raw_history:
        to_email, subject, body = _parse_email_record(record.Email)
        email_history.append({
            'id':       record.id,
            'to_email': to_email,
            'subject':  subject,
            'body':     body,
            'Time':     record.Time,
        })

    emails = supplier_contact_details.objects.filter(
        Supplier=supplier
    ).exclude(Email='').values_list('Email', flat=True)

    context = {
        'supplier':      supplier,
        'email_history': email_history,
        'emails':        emails,
    }
    return render(request, 'suppliers/email_history.html', context)


def _parse_email_record(raw):
    """
    Parse a stored email string back into (to_email, subject, body).

    Stored format (set in send_company_email view):
        To: someone@example.com
        Subject: Hello there

        Body text here...

    Falls back gracefully if the format doesn't match
    (e.g. old records stored in a different format).
    """
    to_email = ''
    subject  = ''
    body     = ''

    if not raw:
        return to_email, subject, body

    # split header block from body on first double newline
    if '\n\n' in raw:
        headers_block, body = raw.split('\n\n', 1)
    else:
        headers_block = raw

    for line in headers_block.splitlines():
        if line.startswith('To:'):
            to_email = line[3:].strip()
        elif line.startswith('Subject:'):
            subject = line[8:].strip()

    # if parsing fails (old format), treat the whole thing as the body
    if not to_email and not subject:
        body = raw

    return to_email, subject, body.strip()