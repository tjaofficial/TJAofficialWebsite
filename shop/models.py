from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

# Create your models here.
SIZE_CHOICES = [
    ("XS", "XS"), ("S", "S"), ("M", "M"), ("L", "L"),
    ("XL", "XL"), ("2XL", "2XL"), ("3XL", "3XL"),
]

class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    price_cents = models.PositiveIntegerField()  # store in cents to avoid float issues
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    image_url = models.URLField(blank=True)      # swap to ImageField later if you want
    category = models.ForeignKey('Category', null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    inventory = models.PositiveIntegerField(default=0)  # simple stock tracking
    created_at = models.DateTimeField(auto_now_add=True)  # optional but nice
    updated_at = models.DateTimeField(auto_now=True)  
    has_variants = models.BooleanField(default=False)
    sku = models.CharField(max_length=64, unique=True)

    def min_variant_price_cents(self) -> int:
        if not self.has_variants:
            return self.price_cents
        v = self.variants.filter(is_active=True, inventory__gt=0).order_by('price_cents').first()
        return v.price_cents if v else self.price_cents

    class Meta:
        ordering = ["title"]

    def image_src(self):
        if self.image:
            return self.image.url
        return self.image_url or ""
    
    def clean(self):
        super().clean()
        if not self.image and not self.image_url:
            raise ValidationError("Upload an image or provide an image URL.")
        if self.image and self.image_url:
            raise ValidationError("Use either an upload or a URL, not both.")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:200]
        super().save(*args, **kwargs)

    @property
    def price_display(self) -> str:
        return f"${self.price_cents/100:.2f}"
    
    def related(self, limit=8):
        qs = Product.objects.filter(is_active=True).exclude(pk=self.pk)
        if self.category_id:
            qs = qs.filter(category_id=self.category_id)
        return qs[:limit]

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=8)  # or choices=SIZE_CHOICES if you want to restrict
    price_cents = models.PositiveIntegerField(default=0)
    inventory = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    sku = models.CharField(max_length=64, blank=True)

    class Meta:
        unique_together = [('product', 'size')]
        ordering = ['product__title', 'size']

    def __str__(self):
        return f"{self.product.title} – {self.size}"

class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name="images"
    )
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    alt = models.CharField(max_length=200, blank=True)
    sort = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product} - {self.sort}"

    class Meta:
        ordering = ["sort", "id"]
    
    def image_src(self):
        if self.image:
            return self.image.url

    def clean(self):
        super().clean()
        if not self.image:
            raise ValidationError("Upload an image.")

    def __str__(self):
        return f"{self.product.title} img"
    
class Cart(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="carts")
    session_key = models.CharField(max_length=64, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)
    unit_price_cents = models.PositiveIntegerField(default=0)

    constraints = [
        # For no-size products (variant IS NULL): only one row per (cart, product)
        models.UniqueConstraint(
            fields=["cart", "product"],
            condition=Q(variant__isnull=True),
            name="uniq_cart_product_no_variant",
        ),
        # For sized products (variant NOT NULL): only one row per (cart, product, variant)
        models.UniqueConstraint(
            fields=["cart", "product", "variant"],
            condition=Q(variant__isnull=False),
            name="uniq_cart_product_with_variant",
        ),
    ]
    def line_total_cents(self) -> int:
        return self.unit_price_cents * self.qty

class Order(models.Model):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("pending", "Pending"),
        ("fulfilled", "Fulfilled"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
        ("canceled", "Canceled"),
    ]

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders")
    email = models.EmailField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    number = models.CharField(max_length=20, blank=True, db_index=True)  # e.g., TJA-000123

    subtotal_cents = models.PositiveIntegerField(default=0)
    shipping_cents = models.PositiveIntegerField(default=0)
    tax_cents = models.PositiveIntegerField(default=0)
    total_cents = models.PositiveIntegerField(default=0)

    shipping_method = models.CharField(max_length=40, blank=True)
    ship_to_name = models.CharField(max_length=120, blank=True)
    ship_to_state = models.CharField(max_length=10, blank=True)
    ship_to_city = models.CharField(max_length=120, blank=True)
    ship_to_addr1 = models.CharField(max_length=200, blank=True)
    ship_to_postal = models.CharField(max_length=20, blank=True)

    payment_provider = models.CharField(max_length=20, default="stripe")
    provider_session_id = models.CharField(max_length=120, blank=True)   # Stripe Checkout session id
    provider_payment_intent = models.CharField(max_length=120, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.number or f"Order {self.pk}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)  # protect so we keep history
    title_snapshot = models.CharField(max_length=200)               # snapshot title at purchase time
    price_cents_snapshot = models.PositiveIntegerField()            # snapshot price
    qty = models.PositiveIntegerField(default=1)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)
    size = models.CharField(max_length=8, blank=True) # snapshot for variant label

    def line_cents(self):
        return self.price_cents_snapshot * self.qty

class StripeEvent(models.Model):
    """Idempotency: store processed Stripe event IDs so we never double-handle."""
    event_id = models.CharField(max_length=200, unique=True)
    type = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

class Coupon(models.Model):
    CODE_USES = (
        ("single", "One-time per recipient"),
        ("multi", "Reusable (until expiry or max_uses)")
    )
    code = models.CharField(max_length=40, unique=True)
    percent_off = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    amount_off_cents = models.PositiveIntegerField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    use_type = models.CharField(max_length=10, choices=CODE_USES, default="single")
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    token_ttl_days = models.PositiveIntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)


    def is_live(self):
        now = timezone.now()
        return self.active and (not self.starts_at or self.starts_at <= now) and (not self.ends_at or now <= self.ends_at)

class CouponToken(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="tokens")
    subscriber = models.ForeignKey("subscribers.Subscriber", null=True, blank=True, on_delete=models.SET_NULL)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)


    @property
    def usable(self):
        return (self.used_at is None) and (self.expires_at is None or self.expires_at >= timezone.now())
    
class InventoryLog(models.Model):
    VARIANT = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="inventory_logs")
    delta = models.IntegerField()
    reason = models.CharField(max_length=120)
    ref = models.CharField(max_length=120, blank=True)
    at = models.DateTimeField(auto_now_add=True)


