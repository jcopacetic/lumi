from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from lumi.notifications.models import Notification


@login_required
@require_http_methods(["GET"])
def notifications_panel_handler(request):
    """
    HTMX endpoint - toggles notifications panel display.
    Expects 'display' header: 'true' (to show) or 'false' (to hide)
    """
    # Get current display state from headers
    display_header = request.headers.get("display", "").lower()

    if display_header not in ["true", "false"]:
        return JsonResponse(
            {"error": "Invalid or missing 'display' header"},
            status=400,
        )

    # Current state is what we're transitioning FROM
    current_display = display_header == "true"
    # New state is the opposite
    new_display = not current_display
    new_display_str = "true" if new_display else "false"

    # Get notifications only if we're showing the panel
    notifications = []
    if new_display:
        # Get unseen notifications first
        unseen_notifications = list(
            Notification.get_user_notifications(
                request.user,
                status=Notification.NotificationStatus.UNSEEN,
                limit=20,
            ),
        )

        # Mark them as seen
        unseen_ids = [notif.id for notif in unseen_notifications]
        if unseen_ids:
            Notification.objects.filter(id__in=unseen_ids).update(
                status=Notification.NotificationStatus.SEEN,
            )

        # Get seen notifications (for full panel view)
        seen_notifications = Notification.get_user_notifications(
            request.user,
            status=Notification.NotificationStatus.SEEN,
            limit=10,  # Maybe fewer seen ones
        )

        # Combine them - unseen still have UNSEEN in memory, seen have SEEN
        notifications = unseen_notifications + list(seen_notifications)

        # Mark these notifications as seen in the database
        # but keep them as "unseen" in the list we're sending to template
        notification_ids = [notif.id for notif in notifications]
        if notification_ids:
            Notification.objects.filter(
                id__in=notification_ids,
            ).update(status=Notification.NotificationStatus.SEEN)

    # Render with NEW state - notifications still have UNSEEN status in memory
    template = render_to_string(
        "notifications/snippets/notifications_wrapper.html",
        {
            "display": new_display_str,
            "notifications": notifications,  # These still appear as unseen
        },
    )

    button = render_to_string(
        "global/notifications_icon.html",
        {"display": new_display_str, "unread_notification_count": 0},  # Clear badge
    )

    return HttpResponse(template + button)
