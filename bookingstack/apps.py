from django.apps import AppConfig


class BookingstackConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bookingstack'

    def ready(self):
        # import signals after apps are ready
        from . import signals  # noqa
