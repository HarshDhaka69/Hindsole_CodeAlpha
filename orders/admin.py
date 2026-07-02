from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("line_total",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "user__email", "contact_email", "shipping_full_name")
    list_editable = ("status",)
    inlines = [OrderItemInline]
    readonly_fields = ("subtotal", "tax", "shipping_cost", "total", "created_at", "updated_at", "stock_restored")

    def order_number(self, obj):
        return obj.order_number

    order_number.short_description = "Order #"
