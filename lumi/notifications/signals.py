import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from lumi.notifications.models import Notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Notification)
def send_notification_via_websocket(sender, instance, created, **kwargs):
    """Send notification through WebSocket when notification is created"""
    if not created:
        return  # Only send for newly created notifications

    try:
        channel_layer = get_channel_layer()

        # Get partner_id from the user
        partner_id = getattr(
            getattr(instance.user, "partner_profile", None),
            "id",
            None,
        )

        if not partner_id:
            logger.warning(
                "No partner_id found for user %s",
                instance.user.id,
            )
            return

        group_name = f"partner_{partner_id}"

        # Send notification to WebSocket group
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "send_notification",
                "notification_slug": instance.slug,
            },
        )

        # Also send badge update
        unseen_count = Notification.get_unseen_count(instance.user)
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "update_badge",
                "unseen_count": unseen_count,
            },
        )

        logger.info(
            "Notification %s sent via WebSocket to %s",
            instance.slug,
            group_name,
        )

    except Exception:
        logger.exception(
            "Error sending notification via WebSocket",
        )
