import json
import logging

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string

from lumi.notifications.models import Notification

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Check if user is authenticated
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            logger.warning("Unauthenticated WebSocket connection attempt")
            await self.close(code=4001)
            return

        self.partner_id = self.scope["url_route"]["kwargs"].get("partner_id")

        # Verify user has permission to access this partner's notifications
        has_permission = await self.check_partner_permission(user, self.partner_id)
        if not has_permission:
            logger.warning(
                "User %s denied access to partner %s",
                user.id,
                self.partner_id,
            )
            await self.close(code=4003)
            return

        self.group_name = f"partner_{self.partner_id}"

        try:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name,
            )
            await self.accept()
            logger.info("WebSocket connection accepted: %s", self.group_name)
        except Exception:
            logger.exception("Websocket connection error")
            await self.close()

    async def disconnect(self, exit_code):
        try:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )
            logger.info("Disconnected from group %s", self.group_name)
        except Exception:
            logger.exception("Error during WebSocket disconnection")

    async def receive(self, text_data):
        # Rate limit check
        rate_key = f"ws_rate_{self.scope['user'].id}_{self.partner_id}"
        request_count = cache.get(rate_key, 0)
        request_per_min_limit = 100
        if request_count > request_per_min_limit:  # 100 requests per minute
            logger.warning("Rate limit exceeded for user %s", self.scope["user"].id)
            await self.send(text_data=json.dumps({"error": "Rate limit exceeded"}))
            return

        cache.set(rate_key, request_count + 1, 60)  # 60 second window

        try:
            data = json.loads(text_data)
            handler_type = data.get("type")

            if not handler_type or not hasattr(self, handler_type):
                logger.exception("Invalid handler type received: %s", handler_type)
                return

            handler_args = {"type": handler_type}
            logger.info("Received data: %s", data)

            if handler_type == "send_notification":
                notification_slug = data.get("notification_slug")
                if not notification_slug:
                    logger.exception("Missing 'notification_slug' in received data.")

                handler_args["notification_slug"] = notification_slug

            await self.channel_layer.group_send(self.group_name, handler_args)

        except json.JSONDecodeError:
            logger.exception("Error decoding JSON")
        except Exception:
            logger.exception("Error processing received message")

    async def send_notification(self, event):
        try:
            notification_slug = event.get("notification_slug")
            if not notification_slug:
                logger.exception("Missing 'notification_slug' in event data.")
                return

            notification = await self.get_notification(notification_slug)
            if not notification:
                logger.exception(
                    "Notification with slug %s not found.",
                    notification_slug,
                )
                return

            template = await self.render_notification_template(notification)

            await self.send(template)
            logger.info("Notification template sent for slug: %s", notification_slug)

        except Exception:
            logger.exception("Error in 'send_notification'")

    @database_sync_to_async
    def check_partner_permission(self, user, partner_id):
        """Verify user has permission to access this partner's notifications"""
        try:
            # Adjust based on your permission model
            from lumi.partners.models import Partner  # or wherever your model is

            # Example checks:
            if user.is_staff or user.is_superuser:
                return True

            # Check if user belongs to this partner
            return Partner.objects.filter(
                id=partner_id,
                users=user,  # Adjust based on your relationship
            ).exists()
        except Exception:
            logger.exception("Error checking partner permissions")
            return False

    @database_sync_to_async
    def get_notification(self, notification_slug):
        try:
            notification = Notification.objects.get(slug=notification_slug)
        except ObjectDoesNotExist:
            logger.exception(
                "Notification with slug '%s does not exist.'",
                notification_slug,
            )
            return None
        else:
            return notification

    @sync_to_async
    def render_notification_template(self, notification):
        try:
            render_template = render_to_string(
                "notifications/snippet/notification.html",
                {"notification": notification},
            )
        except Exception:
            logger.exception("Error rendering notification template")
            return json.dumps({"error": "Template rendering failed"})
        else:
            return f'<div id="notifications-wrapper" hx-swap-oob="outerHTML"> \
                {render_template}</div>'

    async def update_badge(self, event):
        """Handle badge count updates"""
        try:
            unseen_count = event.get("unseen_count", 0)

            # Render just the badge update
            badge_html = await self.render_badge_template(unseen_count)

            await self.send(text_data=badge_html)
            logger.info("Badge count updated: %s", unseen_count)

        except Exception:
            logger.exception("Error in 'update_badge'")

    @sync_to_async
    def render_badge_template(self, unseen_count):
        """Render the notification badge with updated count"""
        try:
            template = render_to_string(
                "global/notifications_icon.html",
                {"unread_notification_count": unseen_count},
            )

        except Exception:
            logger.exception("Error rendering badge template")
            return ""
        else:
            return f'<li class="nav-item ms-3" id="notificationsIcon" \
                hx-swap-oob="outerHTML">{template}</li>'
