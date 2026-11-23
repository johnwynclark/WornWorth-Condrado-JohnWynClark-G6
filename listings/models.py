from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Category(models.Model):
    category_name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        ordering = ["category_name"]

    def __str__(self):
        return self.category_name


class Listing(models.Model):
    """LISTINGS table: one clothing item posted by exactly one seller (BR-06)."""

    class Condition(models.TextChoices):
        NEW_WITH_TAGS = "NEW_WITH_TAGS", "New with tags"
        LIKE_NEW = "LIKE_NEW", "Like new"
        GOOD = "GOOD", "Good"
        FAIR = "FAIR", "Fair"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        REMOVED = "REMOVED", "Removed by admin"

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="listings")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="listings")
    title = models.CharField(max_length=150)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    size = models.CharField(max_length=30)
    condition = models.CharField(max_length=15, choices=Condition.choices)
    quantity = models.PositiveIntegerField(default=1)  # never negative (BR-10)
    listing_status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "listings"
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=Q(price__gt=0), name="listing_price_positive")]

    def __str__(self):
        return self.title

    @property
    def is_available(self):
        """Shown as purchasable only when active with stock (BR-09, BR-12)."""
        return self.listing_status == self.Status.ACTIVE and self.quantity > 0

    @property
    def primary_image(self):
        images = list(self.images.all())  # uses prefetch cache when available
        for image in images:
            if image.is_primary:
                return image
        return images[0] if images else None


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="images")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    image = models.ImageField(upload_to="listings/")
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "listing_images"
        ordering = ["-is_primary", "uploaded_at"]

    def __str__(self):
        return f"Image {self.pk} of listing {self.listing_id}"
