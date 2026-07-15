from django.core.mail import send_mail, get_connection
from django.conf import settings

def send_notification_email(email, subject, content, account):
    try:
        connection = get_connection(
            host = account["EMAIL_HOST"],
            port = account["EMAIL_PORT"],
            username = account["EMAIL_HOST_USER"],
            password = account["EMAIL_HOST_PASSWORD"],
            use_tls = account["EMAIL_USE_TLS"],
        )
        print(f"From : {account['EMAIL_HOST_USER']},\nTo : {email},\nSubject : {subject},\nContent : {content},\n")
        # send_mail(
        #     subject = subject,
        #     message = content,
        #     from_email = account["EMAIL_HOST_USER"],
        #     recipient_list = [email],
        #     connection = connection,
        #     fail_silently = False,
        # )
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False