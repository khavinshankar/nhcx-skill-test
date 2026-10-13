from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NhcxConfig(AppConfig):
    name = "care.nhcx"
    verbose_name = _("NHCX")
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # A4/A5 register their A17 hooks at import (services/hooks.py)
        import importlib

        for name in ("care.nhcx.services.preauth", "care.nhcx.services.claim"):
            try:
                importlib.import_module(name)
            except ImportError as e:
                if e.name != name:
                    raise
