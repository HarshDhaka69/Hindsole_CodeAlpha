from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

# US men's sneaker sizing, half-size increments — the real-world increments
# sneaker retailers use. Stored as CharField so "6.5" round-trips cleanly.
SHOE_SIZE_CHOICES = [
    (str(s), str(s))
    for s in [
        6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12, 13,
    ]
]

SILHOUETTE_CHOICES = [
    ("low-top", "Low-Top"),
    ("mid-top", "Mid-Top"),
    ("high-top", "High-Top"),
]

LOW_STOCK_THRESHOLD = 5  # "Only X left" urgency kicks in at or below this


def slugify_words(name: str) -> str:
    """
    Django's slugify() drops punctuation like "/" and "&" entirely rather
    than treating it as a word boundary, which turns names such as
    "Lifestyle/Casual" into the unreadable "lifestylecasual" or
    "Black/Gum" into "blackgum". Replacing common separators with spaces
    first keeps the words distinct in the resulting slug.
    """
    return slugify(name.replace("/", " ").replace("&", " and "))


class Brand(models.Model):
    """
    Kept separate from Product (rather than a plain CharField) so brand
    filtering, brand landing pages, and brand logos all work cleanly off
    a single source of truth.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    logo = models.ImageField(upload_to="brands/", blank=True, null=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("products:list") + f"?brand={self.slug}"


class Category(models.Model):
    """e.g. Running, Basketball, Lifestyle/Casual, Skate."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify_words(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    """e.g. Retro, Limited Drop, Collab, Restock."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """
    The sneaker model/silhouette itself. Stock and colorway-specific
    pricing live one level down on ProductVariant — a Product is the
    catalog entry, a ProductVariant is the actual sellable unit.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")

    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    compare_at_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Original / MSRP price, shown struck-through if higher than price.",
    )
    silhouette = models.CharField(max_length=20, choices=SILHOUETTE_CHOICES, blank=True)
    release_date = models.DateField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Sneaker-specific structured metadata that doesn't need its own table
    # or queries — a good fit for JSONField on Postgres.
    specs = models.JSONField(
        default=dict,
        blank=True,
        help_text='e.g. {"upper": "Mesh/Suede", "midsole": "Foam", "weight_g": 310}',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "is_featured"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["brand", "is_active"]),
            models.Index(fields=["-release_date"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            i = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base_slug}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("products:detail", kwargs={"slug": self.slug})

    @property
    def is_on_sale(self):
        return bool(self.compare_at_price and self.compare_at_price > self.price)

    @property
    def total_stock(self):
        return sum(v.stock_quantity for v in self.variants.all())

    @property
    def is_sold_out(self):
        return self.total_stock <= 0

    @property
    def colorways(self):
        """Distinct colorway names across this product's variants, in a
        stable order, for the colorway-switcher UI on the PDP."""
        seen = []
        for v in self.variants.all():
            if v.colorway_name not in seen:
                seen.append(v.colorway_name)
        return seen

    @property
    def primary_image(self):
        return self.images.first()


class ProductVariant(models.Model):
    """
    The real sellable unit: one specific size + one specific colorway.
    Stock is tracked per-variant, exactly how sneaker retail actually
    works (a Triple White size 9 can be sold out while size 10 isn't).
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    size = models.CharField(max_length=4, choices=SHOE_SIZE_CHOICES)
    colorway_name = models.CharField(max_length=100)
    stock_quantity = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=64, unique=True, blank=True)

    class Meta:
        ordering = ["colorway_name", "size"]
        unique_together = ("product", "size", "colorway_name")
        indexes = [
            models.Index(fields=["product", "colorway_name"]),
        ]

    def __str__(self):
        return f"{self.product.name} — {self.colorway_name} — US {self.size}"

    def save(self, *args, **kwargs):
        if not self.sku:
            base = slugify(self.product.name)[:20].upper().replace("-", "")
            color = slugify(self.colorway_name)[:8].upper().replace("-", "")
            size_part = str(self.size).replace(".", "H")
            base_sku = f"{base}-{color}-{size_part}"
            # Truncating to 20/8 chars can make distinct colorway names
            # collide (e.g. "Crimson Tide" and "Crimson Twist" both
            # truncate to "CRIMSON"), which would otherwise raise an
            # IntegrityError against the unique=True constraint below.
            sku = base_sku
            i = 1
            while ProductVariant.objects.filter(sku=sku).exclude(pk=self.pk).exists():
                i += 1
                sku = f"{base_sku}-{i}"
            self.sku = sku
        super().save(*args, **kwargs)

    @property
    def in_stock(self):
        return self.stock_quantity > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock_quantity <= LOW_STOCK_THRESHOLD


class ProductImage(models.Model):
    """
    Each colorway gets its own gallery so switching colorways on the PDP
    swaps the full image set, not just a swatch.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    colorway_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Leave blank if this image applies to all colorways.",
    )
    alt_text = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.product.name} image #{self.display_order}"
