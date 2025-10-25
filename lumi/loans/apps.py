import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LoansConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "lumi.loans"
    verbose_name = _("loans")

    def ready(self):
        with contextlib.suppress(ImportError):
            import lumi.loans.signals  # noqa: F401
