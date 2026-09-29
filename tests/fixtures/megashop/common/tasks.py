"""Shared Celery tasks — dispatched from controllers via .delay()/.apply_async()/send_task()."""
from celery import shared_task


@shared_task
def sync_to_crm(customer_id):
    from apps.orders.models import AuditLog
    AuditLog.objects.create(action="crm_sync")     # write inside the task (view-side sees the dispatch)


@shared_task
def send_receipt(email):
    return email
