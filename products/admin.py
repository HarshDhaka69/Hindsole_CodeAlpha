from django.contrib import admin
from django.utils.html import format_html

from .models import Brand, Category, Product, ProductImage, ProductVariant, Tag


class ProductVariantInline(admin.TabularInline):
    """
    Critical for sneaker catalogs: lets an admin manage every
    size/colorway stock count for a product on one screen instead of
    hunting through a separate list view.
    """

    model = ProductVariant
    extra = 1
    fields = ("colorway_name", "size", "stock_quantity", "sku")
    readonly_fields = ()


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "preview", "colorway_name", "alt_text", "display_order")
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:48px;border-radius:6px;" />', obj.image.url)
        return "—"

    preview.short_description = "Preview"


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "product_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Products"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    # No prepopulated_fields here deliberately: the admin's client-side
    # slugify (urlify.js) strips "/" outright instead of treating it as a
    # separator, which would pre-fill the slug field with the same
    # unreadable "lifestylecasual" result our Category.save() override
    # exists to avoid — and a pre-filled, non-empty slug field bypasses
    # that override entirely. Leaving the slug field blank lets the
    # correct server-side logic generate it on save.
    readonly_fields = ("slug",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "brand",
        "category",
        "price",
        "compare_at_price",
        "silhouette",
        "is_featured",
        "is_active",
        "total_stock",
        "release_date",
    )
    list_filter = ("brand", "category", "silhouette", "is_featured", "is_active", "tags")
    search_fields = ("name", "description", "variants__sku")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("tags",)
    inlines = [ProductVariantInline, ProductImageInline]
    list_editable = ("is_featured", "is_active")
    date_hierarchy = "release_date"

    fieldsets = (
        (None, {"fields": ("name", "slug", "brand", "category", "tags")}),
        ("Description & specs", {"fields": ("description", "specs", "silhouette")}),
        ("Pricing & availability", {"fields": ("price", "compare_at_price", "release_date")}),
        ("Visibility", {"fields": ("is_featured", "is_active")}),
    )

    def total_stock(self, obj):
        return obj.total_stock

    total_stock.short_description = "Total stock"


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """
    Standalone variant view, useful for quick stock audits across the
    whole catalog rather than product-by-product.
    """

    list_display = ("product", "colorway_name", "size", "stock_quantity", "sku")
    list_filter = ("product__brand",)
    search_fields = ("product__name", "colorway_name", "sku")
    list_editable = ("stock_quantity",)
