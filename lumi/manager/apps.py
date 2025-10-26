import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ManagerConfig(AppConfig):
    name = "lumi.manager"
    verbose_name = _("Managers")

    def ready(self):
        with contextlib.suppress(ImportError):
            import lumi.manager.signals  # noqa: F401
