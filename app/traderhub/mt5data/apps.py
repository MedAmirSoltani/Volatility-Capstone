from django.apps import AppConfig
import os

class Mt5dataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mt5data'

    def ready(self):
        # ✅ Only start the scheduler if we're NOT running management commands like 'migrate'
        if os.environ.get("RUN_MAIN") == "true" and not any(
            cmd in os.sys.argv for cmd in ["migrate", "makemigrations", "collectstatic", "shell"]
        ):
            from . import scheduler
            scheduler.start()
