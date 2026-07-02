from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models

from products.models import SHOE_SIZE_CHOICES


class UserManager(BaseUserManager):
    """Custom manager so createsuperuser / create_user work off email
    instead of expecting Django's default 'username' positional arg."""

    def _create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model using email as the unique identifier instead of
    username. Adds a couple of sneaker-specific conveniences:
    - default_shoe_size: lets returning users skip re-selecting their size
    - phone_number: useful for shipping / order updates
    """

    email = models.EmailField("email address", unique=True)

    # Keep username field present (Django admin / AbstractUser plumbing
    # expects it) but it is no longer required for login.
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)

    phone_number = models.CharField(max_length=20, blank=True)
    default_shoe_size = models.CharField(
        max_length=4,
        choices=SHOE_SIZE_CHOICES,
        blank=True,
        help_text="Used to pre-select size on product pages and at checkout.",
    )
    dark_mode_enabled = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Keep `username` populated (uniquely) so legacy AbstractUser
        # internals that touch it don't choke, without exposing it anywhere.
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)


class Address(models.Model):
    """A saved shipping address for a user's account / checkout autofill."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=120)
    line1 = models.CharField("Address line 1", max_length=200)
    line2 = models.CharField("Address line 2", max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")
    phone_number = models.CharField(max_length=20, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        verbose_name_plural = "addresses"

    def __str__(self):
        return f"{self.full_name} — {self.city}, {self.state}"

    def save(self, *args, **kwargs):
        # Only one default address per user.
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)
        super().save(*args, **kwargs)
