from django.core.mail import send_mail
from django.conf import settings

def send_notification_email(email, subject, content):
    try:
        print(">>>>>>>>>>>>>>>>",email,subject,content)
        # send_mail(
        #     subject=subject,
        #     message=content,
        #     from_email= settings.EMAIL_HOST_USER,
        #     recipient_list=[email],
        #     fail_silently=False,
        # )
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False