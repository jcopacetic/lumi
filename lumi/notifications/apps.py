import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "lumi.notifications"
    verbose_name = _("Notifications")

    def ready(self):
        with contextlib.suppress(ImportError):
            import lumi.notifications.signals  # noqa: F401
