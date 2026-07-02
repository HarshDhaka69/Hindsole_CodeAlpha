from decimal import Decimal

from django.conf import settings
from django.db import models

from products.models import ProductVariant

ORDER_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("processing", "Processing"),
    ("shipped", "Shipped"),
    ("delivered", "Delivered"),
    ("cancelled", "Cancelled"),
]


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="orders"
    )
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="pending")
    # Tracks whether stock has already been returned to inventory for this
    # order, so flipping status to "cancelled" and back (or saving the
    # admin form twice) can't restore the same stock more than once.
    stock_restored = models.BooleanField(default=False)

    # Shipping snapshot — stored on the order itself (not FK'd to Address)
    # so the order record stays accurate even if the address book entry is
    # later edited or deleted.
    shipping_full_name = models.CharField(max_length=120)
    shipping_line1 = models.CharField(max_length=200)
    shipping_line2 = models.CharField(max_length=200, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100, default="India")
    shipping_phone_number = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField()

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Mock payment fields — see README for the documented Stripe upgrade path.
    payment_method = models.CharField(max_length=40, default="mock_card")
    payment_reference = models.CharField(max_length=80, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Order #{self.pk} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Detect a transition into "cancelled" so we can return the
        # reserved stock to inventory — placing an order decrements stock
        # immediately (see orders.views.checkout_review), but nothing
        # previously put it back if the order was later cancelled instead
        # of fulfilled, permanently losing that inventory.
        should_restore_stock = False
        if self.pk and not self.stock_restored:
            previous_status = (
                Order.objects.filter(pk=self.pk).values_list("status", flat=True).first()
            )
            if previous_status != "cancelled" and self.status == "cancelled":
                should_restore_stock = True

        if should_restore_stock:
            self.stock_restored = True

        super().save(*args, **kwargs)

        if should_restore_stock:
            for item in self.items.select_related("variant"):
                if item.variant_id is None:
                    continue  # variant was deleted from the catalog since purchase
                ProductVariant.objects.filter(pk=item.variant_id).update(
                    stock_quantity=models.F("stock_quantity") + item.quantity
                )

    @property
    def order_number(self):
        return f"HS-{self.pk:06d}"


class OrderItem(models.Model):
    """
    A full snapshot of product name, size, colorway, and price at the
    moment of purchase. The FK to ProductVariant is kept for convenience
    (e.g. linking back to the live product), but every display field is
    duplicated here so historical orders are immune to later catalog
    edits, deletions, or price changes.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL, null=True, related_name="order_items"
    )

    product_name = models.CharField(max_length=200)
    brand_name = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=4)
    colorway_name = models.CharField(max_length=100)
    sku = models.CharField(max_length=64, blank=True)

    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} x {self.product_name} ({self.colorway_name}, US {self.size})"

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity
