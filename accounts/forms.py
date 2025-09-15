from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm

User = get_user_model()

class InvitePasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        # Include active users even if they have an unusable password.
        return User._default_manager.filter(
            email__iexact=email,
            is_active=True,
        )
