from celery import shared_task
from apps.portal.models import User


@shared_task
def send_receipt(user_email):
    User.objects.filter(email=user_email).update(display_name="notified")   # users:write (inside task)
