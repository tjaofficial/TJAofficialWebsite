from __future__ import annotations
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator

User = get_user_model()

class CustomerProfile(models.Model):
    SEX_CHOICES = (
        ("M", "Male"),
        ("F", "Female"),
        ("NB", "Non-binary"),
        ("PNTS", "Prefer not to say"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="rewards_profile")
    phone = models.CharField(max_length=32, blank=True)
    birthday = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=4, choices=SEX_CHOICES, blank=True)
    # Shipping (basic single address – expand to Address table later if needed)
    ship_name = models.CharField(max_length=255, blank=True)
    ship_line1 = models.CharField(max_length=255, blank=True)
    ship_line2 = models.CharField(max_length=255, blank=True)
    ship_city = models.CharField(max_length=100, blank=True)
    ship_state = models.CharField(max_length=100, blank=True)
    ship_postal = models.CharField(max_length=20, blank=True)
    ship_country = models.CharField(max_length=2, default="US")


    marketing_opt_in = models.BooleanField(default=False)


    def __str__(self):
        return f"Profile<{self.user_id}>"

class RewardsAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="rewards")
    points_balance = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    signup_bonus_awarded = models.BooleanField(default=False)


    def __str__(self):
        return f"RewardsAccount<{self.user_id}>: {self.points_balance} pts"


    @transaction.atomic
    def apply_ledger(self, *, delta: int, kind: str, source: str, ref:str|None=None, meta:dict|None=None):
        entry = PointsLedger.objects.create(
            account=self,
            delta=delta,
            kind=kind,
            source=source,
            reference=ref,
            meta=meta or {},
        )
        # Update balance
        self.points_balance = models.F("points_balance") + delta
        self.save(update_fields=["points_balance"])
        self.refresh_from_db(fields=["points_balance"]) # resolve F()
        return entry

class PointsLedger(models.Model):
    KIND_CHOICES = (
        ("EARN", "Earn"),
        ("REDEEM", "Redeem"),
        ("ADJUST", "Adjust"),
    )
    SOURCE_CHOICES = (
        ("SIGNUP", "Signup Bonus"),
        ("ORDER", "Store Order"),
        ("TICKET", "Ticket Check‑in"),
        ("MANUAL", "Manual"),
        ("REFUND", "Refund Reversal"),
    )
    account = models.ForeignKey(RewardsAccount, on_delete=models.CASCADE, related_name="ledger")
    created_at = models.DateTimeField(auto_now_add=True)
    delta = models.IntegerField()
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    source = models.CharField(max_length=12, choices=SOURCE_CHOICES)
    reference = models.CharField(max_length=64, blank=True, null=True) # e.g., order_id, ticket_id
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

class EarningRule(models.Model):
    """Simple rules engine. Start with 2 pts/$ for store orders; X pts per ticket check‑in."""
    RULE_CHOICES = (
        ("PER_DOLLAR", "Points per Dollar (orders)"),
        ("PER_TICKET", "Points per Ticket Check‑in"),
    )
    code = models.CharField(max_length=32, unique=True)
    rule_type = models.CharField(max_length=16, choices=RULE_CHOICES)
    multiplier = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} {self.rule_type} x{self.multiplier} (active={self.active})"

class RewardItem(models.Model):
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    points_cost = models.PositiveIntegerField()
    inventory = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.points_cost} pts)"

class Redemption(models.Model):
    account = models.ForeignKey(RewardsAccount, on_delete=models.PROTECT, related_name="redemptions")
    item = models.ForeignKey(RewardItem, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    points_spent = models.PositiveIntegerField()
    fulfilled = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Redeem {self.item} by {self.account.user} ({self.points_spent} pts)"

class GuestCustomer(models.Model):
    """Tracks purchasers who don’t (yet) have a site account.
    Later, we can merge into a RewardsAccount if they sign up with same email/phone."""
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Guest<{self.email}>"

class PurchaseRecord(models.Model):
    """Normalized view of purchases to power dashboards without coupling to store/ticket models."""
    KIND_CHOICES = (("ORDER", "Store Order"), ("TICKET", "Ticket"))
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    external_id = models.CharField(max_length=64, db_index=True) # your Order.id or Ticket.id
    created_at = models.DateTimeField(default=timezone.now)
    subtotal_cents = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")

    # Linked either to a rewards account OR a guest customer
    account = models.ForeignKey(RewardsAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name="purchases")
    guest = models.ForeignKey(GuestCustomer, null=True, blank=True, on_delete=models.SET_NULL, related_name="purchases")

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    meta = models.JSONField(default=dict, blank=True) # arbitrary payload

    class Meta:
        indexes = [
            models.Index(fields=["kind", "external_id"]),
        ]

    def __str__(self):
        who = self.account.user.email if self.account else (self.guest.email if self.guest else "unknown")
        return f"{self.kind} {self.external_id} ({who})"