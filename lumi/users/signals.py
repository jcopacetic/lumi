import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import Signal
from django.dispatch import receiver

from lumi.notifications.models import Notification

logger = logging.getLogger(__name__)

# Define custom signal for when notifications are created
notification_created = Signal()

User = get_user_model()


@receiver(post_save, sender=User)
def send_welcome_notification(sender, instance, created, **kwargs):
    """Create welcome notification when new user is created"""
    if created:
        Notification.create_notification(
            user=instance,
            title="Welcome Partner!",
            html=(
                "<p>Welcome to Luminate Financial Group's Partner Loan Application "
                "Portal. We are excited to let you be a part of this tool and "
                "vertical integration program for providing quick, dependable "
                "financing options for your valued customers.</p>"
            ),
            notification_type=Notification.NotificationType.ACCOUNT,
            action_url="",
            action_text="Check out partner resources here",
            source="partner_signup",
            source_id=str(instance.id),
        )
