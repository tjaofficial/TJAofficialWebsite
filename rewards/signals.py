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
    RewardsAccount.objects.get_or_create(user=instance)