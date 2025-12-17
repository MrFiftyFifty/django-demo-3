from django.contrib import admin
from .models import Category, Manufacturer, Supplier, Product, UserProfile, Order, OrderItem, PickupPoint


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ['name', 'country']
    search_fields = ['name']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_info']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['article', 'name', 'category', 'manufacturer', 'supplier', 'price', 'stock_quantity', 'discount']
    list_filter = ['category', 'manufacturer', 'supplier']
    search_fields = ['article', 'name', 'description']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'role']
    list_filter = ['role']
    search_fields = ['full_name']


@admin.register(PickupPoint)
class PickupPointAdmin(admin.ModelAdmin):
    list_display = ['address']
    search_fields = ['address']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'order_date', 'delivery_date', 'status', 'total_amount']
    list_filter = ['status', 'order_date']
    search_fields = ['user__username', 'pickup_code']
    inlines = [OrderItemInline]
