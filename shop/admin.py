from django.contrib import admin
from .models import Category, Manufacturer, Supplier, Product, UserProfile, Order, OrderItem, PickupPoint


admin.site.register(Category)
admin.site.register(Manufacturer)
admin.site.register(Supplier)
admin.site.register(Product)
admin.site.register(UserProfile)
admin.site.register(PickupPoint)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'order_date', 'status', 'total_amount']
    list_filter = ['status', 'order_date']
    search_fields = ['order_number', 'user__profile__full_name']
    inlines = [OrderItemInline]
