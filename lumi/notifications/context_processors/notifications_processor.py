"""
Context processor to add notification count to all templates.
Add this to your settings.py TEMPLATES OPTIONS context_processors list.
"""

import logging

from django.utils.functional import SimpleLazyObject

from lumi.notifications.models import Notification

logger = logging.getLogger(__name__)


def notifications_processor(request):
    """
    Add unread notification count and list to template context.
    Uses SimpleLazyObject to defer DB queries until template rendering.
    """
    # Default context (safe fallback)
    context = {
        "unread_notification_count": 0,
        "unread_notifications": [],
    }

    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return context

    def get_count():
        try:
            return Notification.get_unseen_count(user)
        except Exception:
            logger.exception("Error fetching notification count for user %s", user)
            return 0

    def get_notifications():
        try:
            return Notification.get_user_notifications(user, status="unseen")
        except Exception:
            logger.exception("Error fetching notifications for user %s", user)
            return []

    context.update(
        {
            "unread_notification_count": SimpleLazyObject(get_count),
            "unread_notifications": SimpleLazyObject(get_notifications),
        },
    )

    return context
