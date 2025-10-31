from django.urls import path

from lumi.notifications.views import notifications_panel_handler

app_name = "notifications"

urlpatterns = [
    path(
        "notifications/panel/handler/",
        view=notifications_panel_handler,
        name="notifications_panel_handler",
    ),
]
