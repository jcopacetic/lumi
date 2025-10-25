import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PartnersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "lumi.partners"
    verbose_name = _("partners")

    def ready(self):
        with contextlib.suppress(ImportError):
            import lumi.partners.signals  # noqa: F401
