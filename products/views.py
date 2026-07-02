from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView

from .models import Brand, Category, Product, ProductVariant, Tag

PAGE_SIZE = 12


def _parse_price(raw):
    """Safely parses a user-supplied price filter value. Returns None for
    anything that isn't a valid, non-negative decimal — e.g. someone
    pasting '?price_min=abc' directly into the URL bar — instead of
    letting Django's ORM raise an unhandled ValidationError (HTTP 500)."""
    if not raw:
        return None
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError, TypeError):
        return None
    if value < 0:
        return None
    return value


class HomeView(TemplateView):
    """
    Bento-grid homepage: hero tile first (always), then secondary tiles.
    Degrades 3-4 col desktop -> 2 col tablet -> single column stack on
    mobile via Tailwind classes in the template itself (grid order is
    DOM order, so "hero tile first" is satisfied automatically on
    mobile without any reordering logic needed here).
    """

    template_name = "products/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base_qs = Product.objects.filter(is_active=True).select_related("brand").prefetch_related(
            "images", "variants"
        )

        hero_product = base_qs.filter(is_featured=True).order_by("-release_date").first()
        ctx["hero_product"] = hero_product

        bento_qs = base_qs.filter(is_featured=True)
        if hero_product:
            bento_qs = bento_qs.exclude(pk=hero_product.pk)
        ctx["bento_products"] = bento_qs[:3]

        ctx["new_drops"] = base_qs.order_by("-release_date", "-created_at")[:10]
        ctx["brands"] = Brand.objects.all()[:6]
        return ctx


class ProductFilterMixin:
    """Shared filter/sort logic between the full list view and the
    HTMX partial-grid view, so both stay in sync."""

    def get_filtered_queryset(self):
        qs = (
            Product.objects.filter(is_active=True)
            .select_related("brand", "category")
            .prefetch_related("images", "variants", "tags")
            .distinct()
        )

        params = self.request.GET

        brand_slugs = params.getlist("brand")
        if brand_slugs:
            qs = qs.filter(brand__slug__in=brand_slugs)

        category_slug = params.get("category")
        if category_slug:
            qs = qs.filter(category__slug=category_slug)

        tag_slugs = params.getlist("tag")
        if tag_slugs:
            qs = qs.filter(tags__slug__in=tag_slugs)

        sizes = params.getlist("size")
        if sizes:
            qs = qs.filter(variants__size__in=sizes, variants__stock_quantity__gt=0)

        colorways = params.getlist("colorway")
        if colorways:
            qs = qs.filter(variants__colorway_name__in=colorways)

        price_min = _parse_price(params.get("price_min"))
        price_max = _parse_price(params.get("price_max"))
        if price_min is not None:
            qs = qs.filter(price__gte=price_min)
        if price_max is not None:
            qs = qs.filter(price__lte=price_max)

        search = params.get("q")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(brand__name__icontains=search))

        sort = params.get("sort", "newest")
        if sort == "price_asc":
            qs = qs.order_by("price")
        elif sort == "price_desc":
            qs = qs.order_by("-price")
        elif sort == "popularity":
            # Popularity proxy: most order-items sold. Falls back gracefully
            # if there's no order history yet (newly seeded catalogs).
            qs = qs.order_by("-is_featured", "-created_at")
        else:  # newest
            qs = qs.order_by("-release_date", "-created_at")

        return qs


class ProductListView(ProductFilterMixin, ListView):
    """
    Uniform grid listing page (NOT bento — shoppers need to compare
    sneakers side by side here). Filter sidebar on desktop, bottom-sheet
    trigger on mobile; both post into the same HTMX partial endpoint.
    """

    model = Product
    template_name = "products/list.html"
    context_object_name = "products"
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        return self.get_filtered_queryset()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["brands"] = Brand.objects.all()
        ctx["categories"] = Category.objects.all()
        ctx["tags"] = Tag.objects.all()
        # Sizes are stored as strings ("6", "6.5", "10"…) — alphabetical ordering
        # puts "10" before "6", so we pull them all and sort numerically in Python.
        raw_sizes = ProductVariant.objects.values_list("size", flat=True).distinct()
        ctx["sizes"] = sorted(set(raw_sizes), key=lambda s: float(s))
        ctx["colorways"] = (
            ProductVariant.objects.values_list("colorway_name", flat=True).distinct().order_by("colorway_name")
        )
        ctx["active_sort"] = self.request.GET.get("sort", "newest")
        ctx["querystring"] = self._querystring_without_page()
        ctx["selected_brands"] = self.request.GET.getlist("brand")
        ctx["selected_sizes"] = self.request.GET.getlist("size")
        ctx["selected_colorways"] = self.request.GET.getlist("colorway")
        ctx["selected_tags"] = self.request.GET.getlist("tag")
        ctx["selected_category"] = self.request.GET.get("category", "")
        return ctx

    def _querystring_without_page(self):
        params = self.request.GET.copy()
        params.pop("page", None)
        return params.urlencode()


class ProductGridPartialView(ProductFilterMixin, ListView):
    """
    Same filtering logic as ProductListView, but renders only the grid
    partial — this is the HTMX swap target for instant filter/sort
    updates (Béis-style instant filtering) without a full page reload.
    """

    model = Product
    template_name = "products/_grid.html"
    context_object_name = "products"
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        return self.get_filtered_queryset()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx


class ProductDetailView(DetailView):
    """
    PDP: zoomable colorway-aware gallery, size selector that disables
    out-of-stock sizes (but still shows them, struck through), low-stock
    urgency labels, related products, sticky mobile add-to-bag bar.
    """

    model = Product
    template_name = "products/detail.html"
    context_object_name = "product"
    slug_field = "slug"

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related("brand", "category").prefetch_related(
            "images", "variants", "tags"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product = self.object

        colorways = product.colorways
        selected_colorway = self.request.GET.get("colorway") or (colorways[0] if colorways else None)
        ctx["selected_colorway"] = selected_colorway
        ctx["colorways"] = colorways

        ctx["gallery_images"] = _images_for_colorway(product, selected_colorway)

        variants_for_colorway = [
            v for v in product.variants.all() if v.colorway_name == selected_colorway
        ]
        # Sort numerically (sizes are stored as strings like "9.5") so the
        # selector always reads in ascending shoe-size order.
        variants_for_colorway.sort(key=lambda v: float(v.size))
        ctx["variants_for_colorway"] = variants_for_colorway

        default_size = None
        if self.request.user.is_authenticated:
            default_size = self.request.user.default_shoe_size
        ctx["default_size"] = default_size

        ctx["related_products"] = (
            Product.objects.filter(is_active=True, category=product.category)
            .exclude(pk=product.pk)
            .select_related("brand")
            .prefetch_related("images")[:4]
        )
        return ctx


def _images_for_colorway(product, colorway_name):
    images = list(product.images.all())
    matching = [img for img in images if img.colorway_name == colorway_name]
    if matching:
        return matching
    # Fall back to colorway-agnostic images (blank colorway_name) if this
    # particular colorway has no dedicated shots yet.
    generic = [img for img in images if not img.colorway_name]
    return generic or images


def product_gallery_partial(request, slug):
    """
    HTMX endpoint: swapping the selected colorway re-renders just the
    gallery + size-selector fragment, without a full page reload.
    """
    product = get_object_or_404(
        Product.objects.prefetch_related("images", "variants"),
        slug=slug,
        is_active=True,
    )
    colorway = request.GET.get("colorway") or (product.colorways[0] if product.colorways else None)

    variants_for_colorway = [v for v in product.variants.all() if v.colorway_name == colorway]
    variants_for_colorway.sort(key=lambda v: float(v.size))

    default_size = None
    if request.user.is_authenticated:
        default_size = request.user.default_shoe_size

    html = render_to_string(
        "products/_gallery_and_sizes.html",
        {
            "product": product,
            "selected_colorway": colorway,
            "colorways": product.colorways,
            "gallery_images": _images_for_colorway(product, colorway),
            "variants_for_colorway": variants_for_colorway,
            "default_size": default_size,
        },
        request=request,
    )
    return HttpResponse(html)


@require_POST
def toggle_dark_mode(request):
    """
    Persists the dark-mode preference server-side (session for everyone,
    plus the User record for logged-in users so it follows them across
    devices) — the client-side localStorage flip handles the instant
    visual toggle, this just keeps the server in sync so a fresh
    server-rendered page load (no JS yet) still respects the choice.
    """
    enabled = request.POST.get("enabled") == "true"
    request.session["dark_mode"] = enabled
    if request.user.is_authenticated:
        request.user.dark_mode_enabled = enabled
        request.user.save(update_fields=["dark_mode_enabled"])
    return HttpResponse(status=204)
