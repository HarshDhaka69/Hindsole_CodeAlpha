import random
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import Brand, Category, Product, ProductImage, ProductVariant, Tag, slugify_words

SIZES = ["6", "6.5", "7", "7.5", "8", "8.5", "9", "9.5", "10", "10.5", "11", "11.5", "12", "13"]

# Generic / original silhouette names per the brief — structured the way
# real sneaker catalogs are, but not copies of trademarked names.
CATALOG = [
    {
        "name": "Court Classic Low",
        "brand": "Northbridge",
        "category": "Lifestyle/Casual",
        "silhouette": "low-top",
        "price": "110.00",
        "compare_at_price": None,
        "colorways": ["Triple White", "Black/Gum", "University Blue"],
        "tags": ["Retro"],
        "specs": {"upper": "Leather", "midsole": "Rubber cup sole", "weight_g": 320},
    },
    {
        "name": "Trail Runner 2.0",
        "brand": "Ridgepoint",
        "category": "Running",
        "silhouette": "low-top",
        "price": "145.00",
        "compare_at_price": "165.00",
        "colorways": ["Core Black", "Sail/Orange", "Olive Camo"],
        "tags": ["Restock"],
        "specs": {"upper": "Ripstop mesh", "midsole": "Foam", "weight_g": 298},
    },
    {
        "name": "Retro High '85",
        "brand": "Apex",
        "category": "Basketball",
        "silhouette": "high-top",
        "price": "190.00",
        "compare_at_price": None,
        "colorways": ["Bred", "Chicago", "Royal"],
        "tags": ["Retro", "Limited Drop"],
        "specs": {"upper": "Full-grain leather", "midsole": "Encapsulated Air", "weight_g": 430},
    },
    {
        "name": "Canvas Original",
        "brand": "Northbridge",
        "category": "Lifestyle/Casual",
        "silhouette": "low-top",
        "price": "65.00",
        "compare_at_price": None,
        "colorways": ["Optical White", "Black Mono", "Natural Ecru"],
        "tags": [],
        "specs": {"upper": "Canvas", "midsole": "Vulcanized rubber", "weight_g": 310},
    },
    {
        "name": "Suede Classic",
        "brand": "Meridian",
        "category": "Skate",
        "silhouette": "low-top",
        "price": "85.00",
        "compare_at_price": None,
        "colorways": ["Burgundy/Cream", "Forest Green", "Slate Grey"],
        "tags": ["Retro"],
        "specs": {"upper": "Suede", "midsole": "EVA foam", "weight_g": 340},
    },
    {
        "name": "Velocity Mid",
        "brand": "Apex",
        "category": "Basketball",
        "silhouette": "mid-top",
        "price": "175.00",
        "compare_at_price": "200.00",
        "colorways": ["Phantom Black", "Arctic White"],
        "tags": ["Collab", "Limited Drop"],
        "specs": {"upper": "Engineered knit", "midsole": "Dual-density foam", "weight_g": 410},
    },
    {
        "name": "Glide Knit Runner",
        "brand": "Ridgepoint",
        "category": "Running",
        "silhouette": "low-top",
        "price": "135.00",
        "compare_at_price": None,
        "colorways": ["Volt/Black", "Grey Heather"],
        "tags": [],
        "specs": {"upper": "Flyknit-style upper", "midsole": "Responsive foam", "weight_g": 260},
    },
    {
        "name": "Heritage Chukka",
        "brand": "Meridian",
        "category": "Lifestyle/Casual",
        "silhouette": "mid-top",
        "price": "120.00",
        "compare_at_price": None,
        "colorways": ["Tobacco", "Charcoal"],
        "tags": ["Restock"],
        "specs": {"upper": "Nubuck", "midsole": "Crepe sole", "weight_g": 380},
    },
    {
        "name": "Skyline High",
        "brand": "Northbridge",
        "category": "Lifestyle/Casual",
        "silhouette": "high-top",
        "price": "165.00",
        "compare_at_price": "185.00",
        "colorways": ["Midnight Navy", "Bone White", "Rust Clay"],
        "tags": ["Limited Drop"],
        "is_featured": True,
        "description": (
            "The Skyline High takes Northbridge's lifestyle DNA and stretches it "
            "upward — a tall, clean silhouette built on a stacked EVA wedge for "
            "all-day comfort without sacrificing the dressed-up look. Premium "
            "full-grain leather wraps the upper, with a perforated toe box for "
            "breathability and a removable cork footbed that molds to your foot "
            "over time. Internal ankle padding and a reinforced heel counter keep "
            "the high-top collar locked in without feeling stiff. Pairs equally "
            "well with raw denim or tailored trousers — the kind of shoe that "
            "quietly elevates whatever you put it with."
        ),
        "specs": {
            "upper": "Premium full-grain leather with perforated toe box",
            "midsole": "Stacked EVA wedge with cork footbed",
            "weight_g": 395,
        },
    },
]

PLACEHOLDER_IMAGE_COLORS = {
    "Triple White": "F5F2EC",
    "Black/Gum": "2B2622",
    "University Blue": "3F6FA8",
    "Core Black": "211D1A",
    "Sail/Orange": "DE6A2C",
    "Olive Camo": "5C5E3F",
    "Bred": "7B2030",
    "Chicago": "C3501A",
    "Royal": "2E4C8C",
    "Optical White": "FAF7F2",
    "Black Mono": "171411",
    "Natural Ecru": "E9E0D2",
    "Burgundy/Cream": "6E2A3A",
    "Forest Green": "31503B",
    "Slate Grey": "5C5048",
    "Phantom Black": "171411",
    "Arctic White": "F2ECE2",
    "Volt/Black": "C7E03B",
    "Grey Heather": "A0907D",
    "Tobacco": "7B5234",
    "Charcoal": "43392F",
    "Midnight Navy": "1B2A4A",
    "Bone White": "EDE6D8",
    "Rust Clay": "A8502E",
}


def _shade(hex_color, factor):
    """Lightens (factor>1) or darkens (factor<1) a hex color, used to build
    a two-stop gradient from a single base color per colorway."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    r, g, b = (min(255, max(0, int(c * factor))) for c in (r, g, b))
    return f"{r:02X}{g:02X}{b:02X}"


def _readable_text_color(hex_color):
    """Picks black or white label text depending on background luminance,
    so light colorways (Triple White, Sail/Orange) stay legible."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#171411" if luminance > 0.6 else "#FFFFFF"


def _svg_placeholder(product_name, colorway, hex_color):
    """
    Generates a polished demo product image: a gradient card in the
    colorway's base color with an abstract minimalist sole-silhouette
    mark (the kind of clean line-mark used on real sneaker-brand
    packaging/web assets) plus product name and colorway typography.

    This intentionally stays abstract rather than attempting a literal
    illustrated sneaker — keeps the result clean and consistent across
    every colorway without needing real photography on hand (and avoids
    any copyright concerns around reproducing real product photos).
    """
    light = _shade(hex_color, 1.35)
    dark = _shade(hex_color, 0.62)
    text_color = _readable_text_color(hex_color)
    text_opacity = "0.55" if text_color == "#171411" else "0.6"
    mark_opacity = "0.55" if text_color == "#171411" else "0.96"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#{light}"/>
      <stop offset="100%" stop-color="#{dark}"/>
    </linearGradient>
    <radialGradient id="vignette" cx="50%" cy="38%" r="75%">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0.22"/>
    </radialGradient>
  </defs>
  <rect width="800" height="800" fill="url(#bg)"/>
  <rect width="800" height="800" fill="url(#vignette)"/>

  <ellipse cx="400" cy="455" rx="170" ry="14" fill="#000000" opacity="0.18"/>

  <g transform="translate(400,380)" opacity="{mark_opacity}">
    <path d="M-180,40 C-180,10 -150,-20 -90,-35 C-30,-50 40,-48 100,-25
             C140,-10 165,10 165,35 C165,55 145,68 110,68
             L-140,68 C-165,68 -180,58 -180,40 Z"
      fill="none" stroke="{text_color}" stroke-width="10" stroke-linejoin="round"/>
    <path d="M-150,55 L130,55" stroke="{text_color}" stroke-width="14" stroke-linecap="round"/>
    <path d="M-60,-32 C-10,-44 50,-42 95,-23" fill="none" stroke="{text_color}" stroke-width="5" opacity="0.5" stroke-linecap="round"/>
  </g>

  <text x="400" y="560" font-family="sans-serif" font-size="13" font-weight="700" letter-spacing="6" fill="{text_color}" opacity="{text_opacity}"
    text-anchor="middle">HINDSOLE</text>
  <text x="400" y="600" font-family="sans-serif" font-size="32" font-weight="700" fill="{text_color}"
    text-anchor="middle">{product_name}</text>
  <text x="400" y="632" font-family="sans-serif" font-size="20" font-weight="500" fill="{text_color}" opacity="{text_opacity}"
    text-anchor="middle">{colorway}</text>
</svg>"""
    safe_name = f"{product_name}-{colorway}".lower().replace(" ", "-").replace("/", "-")
    return ContentFile(svg.encode("utf-8"), name=f"{safe_name}.svg")


class Command(BaseCommand):
    help = "Seeds the HINDSOLE catalog with realistic demo brands, categories, tags, and products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing catalog data before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing catalog data...")
            ProductImage.objects.all().delete()
            ProductVariant.objects.all().delete()
            Product.objects.all().delete()
            Brand.objects.all().delete()
            Category.objects.all().delete()
            Tag.objects.all().delete()

        brands = {}
        for name in {item["brand"] for item in CATALOG}:
            brand, _ = Brand.objects.get_or_create(name=name)
            brands[name] = brand

        categories = {}
        for name in {item["category"] for item in CATALOG}:
            category, _ = Category.objects.get_or_create(name=name)
            categories[name] = category

        tags = {}
        for tag_name in {t for item in CATALOG for t in item["tags"]}:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            tags[tag_name] = tag

        today = date.today()
        created_count = 0

        for index, item in enumerate(CATALOG):
            product, created = Product.objects.get_or_create(
                name=item["name"],
                defaults={
                    "brand": brands[item["brand"]],
                    "category": categories[item["category"]],
                    "silhouette": item["silhouette"],
                    "price": item["price"],
                    "compare_at_price": item["compare_at_price"],
                    "description": item.get("description") or (
                        f"The {item['name']} from {item['brand']} — built for everyday wear "
                        f"with collector-grade detailing. A staple silhouette, reworked."
                    ),
                    "release_date": today - timedelta(days=random.randint(0, 240)),
                    "is_featured": item.get("is_featured", index < 4),
                    "is_active": True,
                    "specs": item["specs"],
                },
            )
            if not created:
                continue

            created_count += 1
            for tag_name in item["tags"]:
                product.tags.add(tags[tag_name])

            for colorway in item["colorways"]:
                hex_color = PLACEHOLDER_IMAGE_COLORS.get(colorway, "7D6F60")
                image = ProductImage(
                    product=product,
                    colorway_name=colorway,
                    alt_text=f"{product.name} in {colorway}",
                    display_order=0,
                )
                image.image.save(
                    f"{product.slug}-{slugify_words(colorway)}.svg",
                    _svg_placeholder(product.name, colorway, hex_color),
                    save=True,
                )

                for size in SIZES:
                    # Vary stock to exercise the low-stock / sold-out UI states.
                    roll = random.random()
                    if roll < 0.08:
                        stock = 0
                    elif roll < 0.25:
                        stock = random.randint(1, 5)
                    else:
                        stock = random.randint(6, 40)

                    ProductVariant.objects.create(
                        product=product,
                        size=size,
                        colorway_name=colorway,
                        stock_quantity=stock,
                    )

        self.stdout.write(self.style.SUCCESS(f"Seeded {created_count} product(s)."))
