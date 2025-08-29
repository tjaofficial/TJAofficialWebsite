from django.apps import AppConfig


class PagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pages'

    def ready(self):
        from django.contrib.auth.signals import user_logged_in
        from django.dispatch import receiver
        from .cart_utils import merge_session_into_user_cart

        @receiver(user_logged_in)
        def on_login(sender, user, request, **kwargs):
            merge_session_into_user_cart(request, user)