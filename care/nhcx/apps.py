from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NhcxConfig(AppConfig):
    name = "care.nhcx"
    verbose_name = _("NHCX")
    default_auto_field = "django.db.models.BigAutoField"
