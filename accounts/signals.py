from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from cart.cart_logic import merge_session_cart_into_user_cart


@receiver(user_logged_in)
def merge_cart_on_login(sender, request, user, **kwargs):
    """
    Catches login from every path — Django's built-in LoginView, the
    signup flow, password-reset-then-login, anything — so the
    anonymous session cart always gets folded into the user's cart.
    """
    merge_session_cart_into_user_cart(request, user)
