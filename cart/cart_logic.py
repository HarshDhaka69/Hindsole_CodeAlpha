"""
Cart resolution + the anonymous-to-user merge that happens on login.

Design:
- Anonymous visitors get a Cart row keyed by their session key (not just
  raw session data) so cart contents survive things like switching
  devices on the same session backend, and so CartItem can cleanly FK a
  ProductVariant with quantity/stock validation in one place.
- On login, any anonymous cart tied to the now-stale session key is
  merged into the user's persistent cart (quantities summed, capped at
  available stock), then the anonymous cart is deleted.
"""

from django.db import transaction

from cart.models import Cart, CartItem


def _ensure_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    session_key = _ensure_session_key(request)
    cart, _ = Cart.objects.get_or_create(user=None, session_key=session_key)
    return cart


@transaction.atomic
def merge_session_cart_into_user_cart(request, user):
    """
    Call this right after login. Folds the anonymous session cart's items
    into the user's persistent cart, summing quantities for variants that
    appear in both (capped at stock), then removes the now-empty
    anonymous cart.

    Uses `request.pre_login_session_key` (set by CartMiddleware before
    any view runs) in preference to `request.session.session_key`,
    because Django's login() rotates the session key for fixation
    protection before this is typically called.
    """
    session_key = getattr(request, "pre_login_session_key", None) or request.session.session_key
    if not session_key:
        return

    try:
        anon_cart = Cart.objects.get(user=None, session_key=session_key)
    except Cart.DoesNotExist:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)

    for anon_item in anon_cart.items.select_related("variant"):
        stock = anon_item.variant.stock_quantity
        existing = user_cart.items.filter(variant=anon_item.variant).first()
        if existing:
            new_qty = existing.quantity + anon_item.quantity
            # `stock or new_qty` is wrong when stock is genuinely 0 (falsy),
            # since `0 or new_qty` evaluates to new_qty — i.e. "no cap" —
            # exactly when we most need to cap at zero. Compare explicitly.
            capped_qty = min(new_qty, stock) if stock is not None else new_qty
            if capped_qty <= 0:
                existing.delete()
            else:
                existing.quantity = capped_qty
                existing.save()
        else:
            capped_qty = min(anon_item.quantity, stock) if stock is not None else anon_item.quantity
            if capped_qty > 0:
                CartItem.objects.create(
                    cart=user_cart, variant=anon_item.variant, quantity=capped_qty
                )

    anon_cart.delete()
