from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import CustomerProfile, RewardsAccount
from django.contrib.auth.models import AbstractUser

User = get_user_model()

SIGNUP_BONUS_POINTS = 10

@receiver(post_save, sender=User)
def create_profile_and_rewards(sender, instance:AbstractUser, created, **kwargs):
    if not created:
        return
    CustomerProfile.objects.get_or_create(user=instance)
    acc, _ = RewardsAccount.objects.get_or_create(user=instance)
    if not acc.signup_bonus_awarded:
        acc.apply_ledger(delta=SIGNUP_BONUS_POINTS, kind="EARN", source="SIGNUP", ref="signup")
        acc.signup_bonus_awarded = True
        acc.save(update_fields=["signup_bonus_awarded"])