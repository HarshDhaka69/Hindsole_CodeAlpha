from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from products.models import ProductVariant

from .models import CartItem


def cart_view(request):
    cart = request.cart
    return render(request, "cart/cart.html", {"cart": cart})


@require_POST
def add_to_cart(request):
    """
    HTMX endpoint: adds a variant to the cart, then re-renders the
    mini-cart body so the slide-in panel reflects the new contents
    immediately (the calling template also flips `miniCartOpen` open).

    Every outcome — success or error — also swaps a toast into
    #cart-toast-region via hx-swap-oob, since Django's messages framework
    only renders on the next full-page load and would otherwise never be
    seen on these HTMX partial responses.
    """
    variant_id = request.POST.get("variant_id")
    try:
        quantity = int(request.POST.get("quantity", 1) or 1)
    except (TypeError, ValueError):
        quantity = 1
    # Guard against negative/zero/absurd values reaching the DB — the UI
    # never sends anything but 1 today, but a crafted request shouldn't be
    # able to trigger an IntegrityError (PositiveIntegerField CHECK
    # constraint) or silently corrupt cart state.
    quantity = max(1, min(quantity, 99))

    if not variant_id:
        # The client-side onclick guard should prevent reaching here in
        # normal use (it scrolls to the size selector instead of
        # submitting), but handle it gracefully on the server too.
        #
        # Status 200, not 422/409: htmx 1.x (pinned in base.html) only
        # swaps response content for 2xx status codes by default. A 4xx
        # here would mean this toast never actually renders, even though
        # the HTML is correctly generated — verified against htmx's own
        # docs and confirmed this isn't fixed until htmx 4.0. This is a
        # normal, expected application state for the UI to communicate,
        # not a server error, so 200 is the correct choice here anyway.
        return _toast_response(request, "Please select a size first.", is_error=True)

    variant = get_object_or_404(ProductVariant, pk=variant_id)

    if variant.stock_quantity <= 0:
        return _toast_response(request, "Sorry, that size just sold out.", is_error=True)

    cart = request.cart

    item, created = CartItem.objects.get_or_create(cart=cart, variant=variant, defaults={"quantity": 0})
    new_quantity = item.quantity + quantity
    # `if variant.stock_quantity` is wrong once stock can legitimately be 0
    # (falsy) — it would fall through to "no cap" exactly when capping
    # matters most. We already reject stock<=0 above, so this is a plain
    # numeric comparison now.
    capped_quantity = min(new_quantity, variant.stock_quantity)
    item.quantity = capped_quantity
    item.save()

    if capped_quantity < new_quantity:
        # Asked for more than is left in stock — still added what was
        # available, but say so rather than silently adding a smaller
        # amount than requested.
        toast = (
            f"Added {variant.product.name} (US {variant.size}) — only "
            f"{capped_quantity} left, so that's what's in your bag."
        )
    else:
        toast = f"Added {variant.product.name} ({variant.colorway_name}, US {variant.size}) to your bag."

    response = _mini_cart_response(request, toast_message=toast)
    response["HX-Trigger"] = "cart-item-added"
    return response


@require_POST
def update_cart_item(request, item_id):
    cart = request.cart
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)

    action = request.POST.get("action")
    if action == "increment":
        if item.quantity < item.variant.stock_quantity:
            item.quantity += 1
            item.save()
    elif action == "decrement":
        item.quantity -= 1
        if item.quantity <= 0:
            item.delete()
        else:
            item.save()
    else:
        try:
            quantity = int(request.POST.get("quantity", item.quantity))
        except ValueError:
            quantity = item.quantity
        quantity = max(0, min(quantity, item.variant.stock_quantity))
        if quantity == 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save()

    target = request.POST.get("target", "cart_page")
    if target == "mini_cart":
        return _mini_cart_response(request)
    return _cart_page_response(request)


@require_POST
def remove_cart_item(request, item_id):
    cart = request.cart
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()

    target = request.POST.get("target", "cart_page")
    if target == "mini_cart":
        return _mini_cart_response(request)
    return _cart_page_response(request)


def _mini_cart_response(request, toast_message=None):
    html = render_to_string("cart/_mini_cart_items.html", {"cart": request.cart}, request=request)
    if toast_message:
        html += render_to_string(
            "partials/_cart_toast.html",
            {"toast_message": toast_message, "is_error": False},
            request=request,
        )
    return _raw_html(html)


def _cart_page_response(request):
    html = render_to_string("cart/_cart_items.html", {"cart": request.cart}, request=request)
    return _raw_html(html)


def _toast_response(request, message, is_error=False, status=200):
    """For error paths (no variant_id, sold out, etc.) that still need to
    swap *something* into #mini-cart-body — both add-to-cart triggers
    target that element directly, so an OOB-only response would otherwise
    wipe out whatever was already in the cart via an empty innerHTML swap.
    Re-rendering the (unchanged) cart contents alongside the OOB toast
    keeps that swap a no-op while still surfacing the error message."""
    html = render_to_string("cart/_mini_cart_items.html", {"cart": request.cart}, request=request)
    html += render_to_string(
        "partials/_cart_toast.html",
        {"toast_message": message, "is_error": is_error},
        request=request,
    )
    return HttpResponse(html, status=status)


def _raw_html(html):
    return HttpResponse(html)
