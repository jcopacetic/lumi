import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HubspotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "lumi.hubspot"
    verbose_name = _("Hubspot")

    def ready(self):
        with contextlib.suppress(ImportError):
            import lumi.hubspot.signals  # noqa: F401
