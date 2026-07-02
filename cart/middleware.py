"""
Ensures every request — anonymous or authenticated — has a resolved
`request.cart` available, without every view needing to repeat the
get-or-create dance.

Also stashes the pre-login session key on the request object. Django's
login() calls request.session.cycle_key() (session-fixation protection)
*before* the user_logged_in signal fires, so by the time a signal
handler runs, request.session.session_key is already the new key — the
anonymous cart saved under the old key would otherwise become
unreachable. Capturing it here, before any view (including the login
view) runs, gives the post-login merge a reliable value to use.
"""

from django.utils.functional import SimpleLazyObject

from cart.cart_logic import get_or_create_cart


class CartMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.pre_login_session_key = request.session.session_key
        # SimpleLazyObject (the same mechanism Django uses for
        # request.user) defers the get_or_create_cart() DB hit until the
        # cart is actually touched, so static-file and other
        # non-commerce requests pay zero DB cost. Unlike a hand-rolled
        # proxy, it correctly impersonates the real Cart instance once
        # resolved, so it's safe to use directly in ORM filters/FKs
        # (e.g. CartItem.objects.get_or_create(cart=request.cart)).
        request.cart = SimpleLazyObject(lambda: get_or_create_cart(request))
        response = self.get_response(request)
        return response
