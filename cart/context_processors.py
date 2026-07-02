def cart(request):
    """Makes the resolved cart (and a quick quantity badge count) available
    in every template without each view needing to pass it explicitly."""
    current_cart = getattr(request, "cart", None)
    return {
        "cart": current_cart,
        "cart_quantity": current_cart.total_quantity if current_cart else 0,
    }
