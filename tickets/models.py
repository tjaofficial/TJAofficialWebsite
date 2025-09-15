from django.db import models, transaction
from django.utils import timezone
import uuid
from datetime import timedelta
from django.conf import settings

RESERVE_TTL_MIN = 30 # how long a cart hold lasts before auto-release

class TicketType(models.Model):
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="ticket_types")
    name = models.CharField(max_length=120)            # e.g., GA, VIP, Early Bird
    price_cents = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()           # total available
    sales_start = models.DateTimeField(null=True, blank=True)
    sales_end = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    max_per_order = models.PositiveIntegerField(null=True, blank=True)  # optional cap per checkout

    def is_on_sale(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.active:
            return False
        if self.sales_start and now < self.sales_start:
            return False
        if self.sales_end and now > self.sales_end:
            return False
        return True

    def reserved_qty(self):
        return (self.reservations
                    .filter(expires_at__gt=timezone.now(), fulfilled=False)
                    .aggregate(models.Sum("qty"))["qty__sum"] or 0)

    def sold_qty(self):
        return self.tickets.count()

    def remaining(self):
        return max(0, self.quantity - self.sold_qty() - self.reserved_qty())
    
        # --- add these properties ---
    @property
    def on_sale(self):
        return self.is_on_sale()

    @property
    def remaining_qty(self):
        return self.remaining()

    def __str__(self):
        return f"{self.event} — {self.name}"

class Ticket(models.Model):
    PAYMENT_CHOICES = [
        ("card", "Card/Stripe"),
        ("cash", "Cash"),
        ("comp", "Comp"),
    ]
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT, related_name="tickets")
    purchaser_name = models.CharField(max_length=120, blank=True)
    purchaser_email = models.EmailField(blank=True)
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=240, blank=True)

    sold_by_artist = models.ForeignKey("pages.Artist", null=True, blank=True,
                                       on_delete=models.SET_NULL, related_name="tickets_sold")
    sold_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="tickets_issued")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="card")

    def is_checked_in(self) -> bool:
        return self.checked_in_at is not None

    def check_in(self):
        if not self.checked_in_at:
            self.checked_in_at = timezone.now()
            self.save(update_fields=["checked_in_at"])

    def __str__(self):
        return f"{self.ticket_type.name} • {self.qr_token}"
    
class TicketReservation(models.Model):
    """
    Short-lived hold for inventory. Fulfilled by webhook after payment succeeds.
    """
    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE, related_name="reservations")
    qty = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    fulfilled = models.BooleanField(default=False)
    stripe_session_id = models.CharField(max_length=255, blank=True, db_index=True)
    purchaser_email = models.EmailField(blank=True)
    purchaser_name = models.CharField(max_length=120, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["stripe_session_id"]),
        ]

    @classmethod
    def create_reservations(cls, selections, purchaser_email="", purchaser_name="", stripe_session_id=""):
        """
        selections = list of dicts: [{"tt": TicketType, "qty": 2}, ...]
        Performs row-level locking and validates availability to prevent oversell.
        """
        now = timezone.now()
        expires = now + timedelta(minutes=RESERVE_TTL_MIN)
        created = []
        with transaction.atomic():
            # lock all involved types
            locked_types = (TicketType.objects
                            .select_for_update()
                            .filter(id__in=[s["tt"].id for s in selections]))
            ttype_by_id = {t.id: t for t in locked_types}
            # re-check availability under lock
            for sel in selections:
                tt = ttype_by_id[sel["tt"].id]
                if not tt.is_on_sale():
                    raise ValueError(f"{tt.name} not on sale.")
                if tt.max_per_order and sel["qty"] > tt.max_per_order:
                    raise ValueError(f"Max {tt.max_per_order} per order for {tt.name}.")
                if sel["qty"] <= 0 or sel["qty"] > tt.remaining():
                    raise ValueError(f"Insufficient inventory for {tt.name}.")
            # create holds
            for sel in selections:
                created.append(cls.objects.create(
                    ticket_type=ttype_by_id[sel["tt"].id],
                    qty=sel["qty"],
                    expires_at=expires,
                    purchaser_email=purchaser_email,
                    purchaser_name=purchaser_name,
                    stripe_session_id=stripe_session_id,
                ))
        return created