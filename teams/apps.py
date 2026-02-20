import os

from django.apps import AppConfig
from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError


class TeamsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'teams'

    def ready(self):
        domain = os.environ.get("DJANGO_SITE_DOMAIN", "").strip()
        if not domain or getattr(settings, "SITE_ID", None):
            return
        try:
            from django.contrib.sites.models import Site
        except (OperationalError, ProgrammingError):
            return
        try:
            site = Site.objects.get(domain__iexact=domain)
        except (Site.DoesNotExist, OperationalError, ProgrammingError):
            return
        settings.SITE_ID = site.id
