import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Address
from products.models import ProductVariant

from .forms import ShippingForm
from .models import Order, OrderItem

CHECKOUT_SESSION_KEY = "checkout_shipping_data"


def checkout_shipping(request):
    """
    Step 1 of checkout: cart review happens via the cart page itself
    (the spec's "cart review -> shipping info -> confirmation" maps to
    cart page -> this view -> the review/confirm view below).
    """
    cart = request.cart
    if not cart or not cart.items_qs:
        messages.error(request, "Your bag is empty.")
        return redirect("cart:view")

    initial = {}
    if request.user.is_authenticated:
        initial["contact_email"] = request.user.email
        default_address = request.user.addresses.filter(is_default=True).first() or request.user.addresses.first()
        if default_address:
            initial.update(
                shipping_full_name=default_address.full_name,
                shipping_line1=default_address.line1,
                shipping_line2=default_address.line2,
                shipping_city=default_address.city,
                shipping_state=default_address.state,
                shipping_postal_code=default_address.postal_code,
                shipping_country=default_address.country,
                shipping_phone_number=default_address.phone_number,
            )

    if request.method == "POST":
        form = ShippingForm(request.POST)
        if form.is_valid():
            request.session[CHECKOUT_SESSION_KEY] = form.cleaned_data
            return redirect("orders:checkout_review")
    else:
        form = ShippingForm(initial=initial)

    return render(request, "orders/checkout_shipping.html", {"form": form, "cart": cart})


def checkout_review(request):
    """Step 2: review order + cart contents, then confirm with mock payment."""
    cart = request.cart
    shipping_data = request.session.get(CHECKOUT_SESSION_KEY)

    if not cart or not cart.items_qs:
        messages.error(request, "Your bag is empty.")
        return redirect("cart:view")
    if not shipping_data:
        return redirect("orders:checkout_shipping")

    if request.method == "POST":
        with transaction.atomic():
            # Lock the variants so concurrent checkouts cannot both decrement
            # the same stock row simultaneously (oversell prevention).
            variant_ids = [item.variant_id for item in cart.items_qs]
            locked_variants = {
                v.pk: v
                for v in ProductVariant.objects.select_for_update().filter(pk__in=variant_ids)
            }

            # Validate stock is still available after acquiring the locks.
            insufficient = []
            for item in cart.items_qs:
                variant = locked_variants[item.variant_id]
                if variant.stock_quantity < item.quantity:
                    insufficient.append(
                        f"{variant.product.name} ({variant.colorway_name}, US {variant.size})"
                    )
            if insufficient:
                messages.error(
                    request,
                    "Some items in your bag are no longer available in the requested quantity: "
                    + ", ".join(insufficient) + ". Please review your bag.",
                )
                return redirect("cart:view")

            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                shipping_full_name=shipping_data["shipping_full_name"],
                shipping_line1=shipping_data["shipping_line1"],
                shipping_line2=shipping_data.get("shipping_line2", ""),
                shipping_city=shipping_data["shipping_city"],
                shipping_state=shipping_data["shipping_state"],
                shipping_postal_code=shipping_data["shipping_postal_code"],
                shipping_country=shipping_data["shipping_country"],
                shipping_phone_number=shipping_data.get("shipping_phone_number", ""),
                contact_email=shipping_data["contact_email"],
                subtotal=cart.subtotal,
                tax=cart.tax,
                shipping_cost=cart.shipping_cost,
                total=cart.total,
                status="processing",
                payment_method="mock_card",
                payment_reference=f"MOCK-{uuid.uuid4().hex[:12].upper()}",
            )

            for item in cart.items_qs:
                variant = locked_variants[item.variant_id]
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    product_name=variant.product.name,
                    brand_name=variant.product.brand.name,
                    size=variant.size,
                    colorway_name=variant.colorway_name,
                    sku=variant.sku,
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                )
                # Decrement stock now that the (mock) payment has gone through.
                variant.stock_quantity = max(0, variant.stock_quantity - item.quantity)
                variant.save(update_fields=["stock_quantity"])

            if request.user.is_authenticated and shipping_data.get("save_address"):
                Address.objects.create(
                    user=request.user,
                    full_name=shipping_data["shipping_full_name"],
                    line1=shipping_data["shipping_line1"],
                    line2=shipping_data.get("shipping_line2", ""),
                    city=shipping_data["shipping_city"],
                    state=shipping_data["shipping_state"],
                    postal_code=shipping_data["shipping_postal_code"],
                    country=shipping_data["shipping_country"],
                    phone_number=shipping_data.get("shipping_phone_number", ""),
                )

            cart.items.all().delete()

        request.session.pop(CHECKOUT_SESSION_KEY, None)
        # Allow the confirmation view to verify this session placed the order.
        request.session["last_order_pk"] = order.pk

        return redirect("orders:confirmation", pk=order.pk)

    return render(
        request,
        "orders/checkout_review.html",
        {"cart": cart, "shipping_data": shipping_data},
    )


def order_confirmation(request, pk):
    order = get_object_or_404(Order, pk=pk)
    # Ownership check: a logged-in user may only view their own orders.
    # Anonymous orders (user_id=None) are accessible only via the direct
    # redirect link returned immediately after placement — once a user is
    # authenticated we enforce ownership to prevent order enumeration.
    if request.user.is_authenticated and order.user_id and order.user_id != request.user.id:
        messages.error(request, "That order could not be found.")
        return redirect("products:home")
    # Prevent any authenticated user from peeking at anonymous orders that
    # aren't their own session's most-recently-placed order.
    if request.user.is_authenticated and order.user_id is None:
        # Allow only if this pk matches the order just placed in this session.
        if request.session.get("last_order_pk") != pk:
            messages.error(request, "That order could not be found.")
            return redirect("products:home")
    return render(request, "orders/confirmation.html", {"order": order})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, "orders/order_history.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, "orders/order_detail.html", {"order": order})
