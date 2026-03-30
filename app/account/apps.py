from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'account'
    verbose_name = 'Аккаунт'
    verbose_name_plural = 'Аккаунты'

    def ready(self):
        # Ensure modeltranslation registrations are loaded on startup.
        from . import translation  # noqa: F401
        from .signals import compile_translations_after_migrate

        post_migrate.connect(
            compile_translations_after_migrate,
            sender=self,
            dispatch_uid="account.compile_translations_after_migrate",
        )
