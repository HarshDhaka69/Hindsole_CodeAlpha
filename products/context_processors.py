from django.conf import settings

from products.models import Brand, Category


def site_meta(request):
    """
    Powers the mega-menu / hamburger menu nav (brand + category links) on
    every page, and surfaces the persisted dark-mode preference.
    Also injects commerce settings so every template can render them
    correctly without per-view boilerplate.
    """
    dark_mode = request.session.get("dark_mode", False)
    if request.user.is_authenticated and getattr(request.user, "dark_mode_enabled", False):
        dark_mode = True

    threshold = getattr(settings, "FREE_SHIPPING_THRESHOLD", 150)
    symbol = getattr(settings, "CURRENCY_SYMBOL", "$")

    return {
        "nav_brands": Brand.objects.all()[:8],
        "nav_categories": Category.objects.all(),
        "dark_mode_enabled": dark_mode,
        "site_name": "HINDSOLE",
        "site_tagline": "Every step, in hindsight.",
        # Commerce helpers used in cart/detail templates.
        "FREE_SHIPPING_THRESHOLD": f"{symbol}{threshold:,.0f}",
        "CURRENCY_SYMBOL": symbol,
    }
