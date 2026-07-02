from decimal import Decimal

from django.conf import settings
from django.db import models

from products.models import ProductVariant


class Cart(models.Model):
    """
    A cart belongs to either an authenticated user OR an anonymous
    session key — never both. Anonymous carts get merged into the user's
    cart on login (see cart.cart_logic.merge_session_cart_into_user_cart).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart",
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session_key"],
                condition=models.Q(user__isnull=True),
                name="unique_anon_cart_per_session",
            )
        ]

    def __str__(self):
        owner = self.user.email if self.user_id else f"session:{self.session_key}"
        return f"Cart ({owner})"

    @property
    def items_qs(self):
        return self.items.select_related("variant__product").order_by("id")

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items_qs)

    @property
    def subtotal(self) -> Decimal:
        return sum((item.line_total for item in self.items_qs), Decimal("0.00"))

    @property
    def tax(self) -> Decimal:
        rate = Decimal(str(getattr(settings, "TAX_RATE", 0.0)))
        return (self.subtotal * rate).quantize(Decimal("0.01"))

    @property
    def shipping_cost(self) -> Decimal:
        if self.subtotal == 0:
            return Decimal("0.00")
        threshold = Decimal(str(getattr(settings, "FREE_SHIPPING_THRESHOLD", 0)))
        if self.subtotal >= threshold:
            return Decimal("0.00")
        return Decimal(str(getattr(settings, "STANDARD_SHIPPING_COST", 0)))

    @property
    def total(self) -> Decimal:
        return (self.subtotal + self.tax + self.shipping_cost).quantize(Decimal("0.01"))


class CartItem(models.Model):
    """
    References a specific ProductVariant (size + colorway combo) rather
    than the parent Product — a cart should never be ambiguous about
    which size/colorway was selected.
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "variant")
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} x {self.variant}"

    @property
    def unit_price(self) -> Decimal:
        return self.variant.product.price

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity
