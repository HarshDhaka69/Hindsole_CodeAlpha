"""
Adds one demo product photographed with real product photography instead
of the generated SVG gradient placeholders used by `seed_products`.

Run this AFTER `seed_products` (it doesn't touch or require that command's
data, but the brand/category/tag setup happens there). Requires outbound
internet access to images.unsplash.com, since it actually downloads each
photo — this will not work in network-restricted environments (CI, some
sandboxes); run it locally or anywhere with normal internet access.

    python manage.py seed_unsplash_demo

Every photo below was individually checked before inclusion: each one is
published under the Unsplash License (free for commercial use, no
attribution legally required — see https://unsplash.com/license) and was
selected specifically because it does not feature a recognizable brand
logo or trademarked silhouette, consistent with the rest of this project's
approach of using fictional brand names (Northbridge, Ridgepoint, Apex,
Meridian) to avoid any real-brand IP entanglement. If you swap in your own
photo URLs, apply the same check before using them.
"""

import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from products.models import Brand, Category, Product, ProductImage, ProductVariant, Tag

SIZES = ["6", "6.5", "7", "7.5", "8", "8.5", "9", "9.5", "10", "10.5", "11", "11.5", "12", "13"]

# Each entry: a real, individually-verified Unsplash photo (Unsplash
# License, no visible brand logo) mapped to a colorway name for the demo
# product below. `w=1200` keeps the download reasonably sized while still
# looking sharp on the product detail page's gallery.
UNSPLASH_PHOTOS = [
    {
        "colorway": "Crimson Pair",
        "photo_id": "utRLWdrYK8M",
        "image_url": "https://images.unsplash.com/photo-1675625500632-2d276bd51920"
        "?fm=jpg&q=80&w=1200&auto=format&fit=crop",
        "photographer": "Derrick Payton",
        "photographer_url": "https://unsplash.com/@studio3presents",
        "unsplash_url": "https://unsplash.com/photos/utRLWdrYK8M",
    },
    {
        "colorway": "White & Red",
        "photo_id": "9Kim7qEXiFc",
        "image_url": "https://images.unsplash.com/photo-1689417735464-75b5c12a820f"
        "?fm=jpg&q=80&w=1200&auto=format&fit=crop",
        "photographer": "Raymond Sime",
        "photographer_url": "https://unsplash.com/@raymond36",
        "unsplash_url": "https://unsplash.com/photos/9Kim7qEXiFc",
    },
]

DEMO_PRODUCT = {
    "name": "Studio Edition Low",
    "brand": "Northbridge",
    "category": "Lifestyle/Casual",
    "silhouette": "low-top",
    "price": "12126.00",
    "compare_at_price": None,
    "tags": ["Retro"],
    "description": (
        "A clean, low-profile silhouette shot the way it deserves to be — real studio "
        "photography instead of a flat render. Built on the same cup-sole construction "
        "as the rest of the Northbridge lineup, the Studio Edition Low keeps things "
        "simple: a soft leather upper, minimal branding, and proportions that work as "
        "easily with tailored trousers as they do with denim."
    ),
    "specs": {"upper": "Leather", "midsole": "Rubber cup sole", "weight_g": 315},
}


class Command(BaseCommand):
    help = (
        "Downloads real product photography from Unsplash and creates one demo "
        "product using it (requires internet access to images.unsplash.com)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete this command's demo product (if it already exists) before re-seeding.",
        )

    def handle(self, *args, **options):
        try:
            import requests
        except ImportError as exc:
            raise CommandError(
                "The 'requests' package is required for this command. "
                "Install it with: pip install requests"
            ) from exc

        if options["flush"]:
            deleted, _ = Product.objects.filter(name=DEMO_PRODUCT["name"]).delete()
            if deleted:
                self.stdout.write(self.style.WARNING(f"Removed existing '{DEMO_PRODUCT['name']}'."))

        if Product.objects.filter(name=DEMO_PRODUCT["name"]).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"'{DEMO_PRODUCT['name']}' already exists — skipping. "
                    "Use --flush to replace it."
                )
            )
            return

        # Download every photo FIRST, before writing anything to the
        # database, so a network failure partway through doesn't leave a
        # half-created product behind.
        downloaded = []
        for photo in UNSPLASH_PHOTOS:
            self.stdout.write(f"Downloading {photo['colorway']} photo from Unsplash...")
            try:
                response = requests.get(photo["image_url"], timeout=20)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise CommandError(
                    f"Failed to download {photo['image_url']!r}: {exc}\n"
                    "This command needs outbound internet access to images.unsplash.com — "
                    "it will not work in network-restricted environments."
                ) from exc

            content_type = response.headers.get("Content-Type", "")
            if "image" not in content_type:
                raise CommandError(
                    f"Expected an image response from {photo['image_url']!r}, "
                    f"got Content-Type {content_type!r} instead. The photo may have "
                    "been removed from Unsplash or the URL needs updating."
                )

            # Quick sanity check that we actually got real image bytes, not
            # an HTML error/login page served with a misleading content-type.
            try:
                from PIL import Image

                Image.open(io.BytesIO(response.content)).verify()
            except Exception as exc:
                raise CommandError(
                    f"Downloaded content from {photo['image_url']!r} doesn't look like "
                    f"a valid image: {exc}"
                ) from exc

            downloaded.append((photo, response.content))

        with transaction.atomic():
            brand, _ = Brand.objects.get_or_create(name=DEMO_PRODUCT["brand"])
            category, _ = Category.objects.get_or_create(name=DEMO_PRODUCT["category"])
            tags = [Tag.objects.get_or_create(name=t)[0] for t in DEMO_PRODUCT["tags"]]

            product = Product.objects.create(
                name=DEMO_PRODUCT["name"],
                brand=brand,
                category=category,
                silhouette=DEMO_PRODUCT["silhouette"],
                price=DEMO_PRODUCT["price"],
                compare_at_price=DEMO_PRODUCT["compare_at_price"],
                description=DEMO_PRODUCT["description"],
                is_featured=True,
                is_active=True,
                specs=DEMO_PRODUCT["specs"],
            )
            product.tags.set(tags)

            for photo, content in downloaded:
                image = ProductImage(
                    product=product,
                    colorway_name=photo["colorway"],
                    alt_text=f"{product.name} in {photo['colorway']} — photo by "
                    f"{photo['photographer']} on Unsplash",
                    display_order=0,
                )
                image.image.save(
                    f"{product.slug}-{photo['photo_id']}.jpg",
                    ContentFile(content),
                    save=True,
                )

                for size in SIZES:
                    ProductVariant.objects.create(
                        product=product,
                        size=size,
                        colorway_name=photo["colorway"],
                        stock_quantity=12,
                    )

        self.stdout.write(self.style.SUCCESS(f"Created '{product.name}' with real product photography."))
        self.stdout.write("Photo credits (Unsplash License — no attribution legally required, listed anyway):")
        for photo in UNSPLASH_PHOTOS:
            self.stdout.write(f"  • {photo['colorway']}: {photo['photographer']} — {photo['unsplash_url']}")
