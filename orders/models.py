import secrets

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Address(models.Model):
    """ADDRESSES table: delivery addresses owned by a user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    recipient_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, validators=[RegexValidator(r"^\+?[0-9 \-]{7,20}$", "Enter a valid contact number, e.g. 0917 123 4567.")])
    address_line = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10, validators=[RegexValidator(r"^[0-9A-Za-z\- ]{3,10}$", "Enter a valid postal code.")])

    class Meta:
        db_table = "addresses"
        verbose_name_plural = "addresses"

    def __str__(self):
        return f"{self.recipient_name}, {self.address_line}, {self.city}"

    @property
    def one_line(self):
        return f"{self.address_line}, {self.city}, {self.province} {self.postal_code}"


def generate_reference():
    """Unique public order reference, e.g. WW-20261123-7F3KQ9 (BR-19)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        ref = f"WW-{timezone.localdate():%Y%m%d}-{''.join(secrets.choice(alphabet) for _ in range(6))}"
        if not Order.objects.filter(order_reference=ref).exists():
            return ref


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PROCESSING = "PROCESSING", "Processing"
        SHIPPED = "SHIPPED", "Shipped"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    CANCELLABLE = (Status.PENDING, Status.CONFIRMED)  # BR-22
    # Seller moves an order forward one step at a time; the buyer completes it.
    SELLER_NEXT = {
        Status.PENDING: (Status.CONFIRMED, "Confirm order"),
        Status.CONFIRMED: (Status.PROCESSING, "Start processing"),
        Status.PROCESSING: (Status.SHIPPED, "Mark as shipped"),
    }
    TIMELINE = (Status.PENDING, Status.CONFIRMED, Status.PROCESSING, Status.SHIPPED, Status.COMPLETED)

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name="orders")
    order_reference = models.CharField(max_length=30, unique=True, default=generate_reference)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    order_status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    ordered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "orders"
        ordering = ["-ordered_at"]

    def __str__(self):
        return self.order_reference

    @property
    def can_cancel(self):
        return self.order_status in self.CANCELLABLE

    @property
    def seller_next(self):
        """(next_status, button_label) or None."""
        return self.SELLER_NEXT.get(self.order_status)

    @property
    def timeline_index(self):
        return self.TIMELINE.index(self.order_status) if self.order_status in self.TIMELINE else -1


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    listing = models.ForeignKey("listings.Listing", on_delete=models.PROTECT, related_name="order_items")  # BR-30
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])  # price at purchase (BR-18)
    item_subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        db_table = "order_items"
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="orderitem_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_price__gt=0), name="orderitem_unit_price_positive"),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.listing_id} on {self.order_id}"
