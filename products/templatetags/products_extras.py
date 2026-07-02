from django import template
from django.conf import settings

register = template.Library()


@register.filter
def currency(value):
    """Formats a Decimal/number as '$129.00' using the site currency symbol."""
    if value is None:
        return ""
    symbol = getattr(settings, "CURRENCY_SYMBOL", "$")
    return f"{symbol}{value:,.2f}"


@register.filter
def stock_label(variant):
    """Returns a short urgency label for a ProductVariant, or '' if stock
    is healthy enough not to need one."""
    if variant.stock_quantity <= 0:
        return "Sold out"
    if variant.is_low_stock:
        return f"Only {variant.stock_quantity} left"
    return ""
