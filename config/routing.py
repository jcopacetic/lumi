from django.urls import path

from lumi.notifications.consumer import NotificationConsumer

websocket_urlpatterns = [
    path(
        "ws/partner/<int:partner_id>/notifications/",
        view=NotificationConsumer.as_asgi(),
    ),
]
