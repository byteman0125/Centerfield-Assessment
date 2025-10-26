"""
Django signals for scheduler app.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

from .tasks import execute_wakeup_call


@receiver(post_save, sender='calls.WakeUpCall')
def schedule_wakeup_call(sender, instance, created, **kwargs):
    """Schedule a wake-up call when created or updated."""
    if created and instance.status == 'scheduled':
        # Schedule the call using Celery beat
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute=instance.scheduled_time.minute,
            hour=instance.scheduled_time.hour,
            day_of_month=instance.scheduled_time.day,
            month_of_year=instance.scheduled_time.month,
            day_of_week='*',
        )
        
        task_name = f"wakeup-call-{instance.id}"
        PeriodicTask.objects.update_or_create(
            name=task_name,
            defaults={
                'crontab': schedule,
                'task': 'apps.scheduler.tasks.execute_wakeup_call',
                'args': json.dumps([str(instance.id)]),
                'enabled': True,
                'one_off': True,  # Run only once
            }
        )
