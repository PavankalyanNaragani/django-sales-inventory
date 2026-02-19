from django.contrib import admin
from .models import Product, Inventory, Dealer, Order, OrderItem

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'current_price', 'created_at', 'updated_at')
    search_fields = ('sku', 'name')
    list_filter = ('created_at',)
    ordering = ('-created_at',)

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    # This fulfills the requirement to allow manual stock corrections via admin
    list_display = ('product', 'available_quantity', 'last_updated')
    search_fields = ('product__sku', 'product__name')
    list_editable = ('available_quantity',) # Allows quick stock adjustments directly from the list view

@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ('dealer_code', 'name', 'email', 'phone', 'created_at')
    search_fields = ('dealer_code', 'name', 'email')
    list_filter = ('created_at',)

# Inline admin for OrderItem so they can be viewed/edited directly inside the Order page
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # Fields with editable=False in models.py MUST be added to readonly_fields to be visible
    readonly_fields = ('unit_price', 'line_total')
    fields = ('product', 'quantity', 'unit_price', 'line_total')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'dealer', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'dealer__name', 'dealer__dealer_code')
    inlines = [OrderItemInline]
    
    # order_number and total_amount are auto-calculated/generated, so they must be read-only
    readonly_fields = ('order_number', 'total_amount', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Order Details', {
            'fields': ('order_number', 'dealer', 'status', 'total_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Enforce business rules in the admin panel:
        If the order is Confirmed or Delivered, prevent admins from editing it.
        """
        if obj and obj.status in ['Confirmed', 'Delivered']:
            # Make all fields read-only if the order is past the Draft stage
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields