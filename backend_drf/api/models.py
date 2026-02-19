from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError

class Product(models.Model):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.sku} "

class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='inventory')
    available_quantity = models.PositiveIntegerField(default=0)
    
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.sku} Stock: {self.available_quantity}"

class Dealer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    dealer_code = models.CharField(max_length=50, unique=True, db_index=True)
    address = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    
class Order(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Confirmed', 'Confirmed'),
        ('Delivered', 'Delivered'),
    ]

    # Auto-generated unique order number
    order_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Prevent deleting a dealer if they have orders (Business Rule safety)
    dealer = models.ForeignKey(Dealer, on_delete=models.PROTECT, related_name='orders')
    
    # Order status must transition through specific states
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    
    # Sum of all line_totals (updated when items change)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-generate unique format like 'ORD-YYYYMMDD-XXXX'
        if not self.order_number:
            date_str = timezone.now().strftime('%Y%m%d')
            # Count today's orders to generate the XXXX sequence
            today_orders_count = Order.objects.filter(created_at__date=timezone.now().date()).count()
            sequence = f"{today_orders_count + 1:04d}"
            self.order_number = f"ORD-{date_str}-{sequence}"
        super().save(*args, **kwargs)

    def update_total_amount(self):
        # Auto-calculate total_amount based on all related OrderItems
        total = self.items.aggregate(total=Sum('line_total'))['total'] or 0.00
        self.total_amount = total
        self.save(update_fields=['total_amount'])

    def __str__(self):
        return f"{self.order_number} ({self.status})"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    
    # Prevent deleting a product if it has been ordered
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    
    quantity = models.PositiveIntegerField()
    
    # Price at the time of order should be preserved
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    
    # quantity * unit_price (calculated automatically)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        # Only set unit_price if it's a new item or if the order is still a Draft
        if not self.pk and not self.unit_price:
            self.unit_price = self.product.current_price
            
        # Auto-calculate line_total
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        
        # Trigger parent order to recalculate its total_amount
        self.order.update_total_amount()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        # Recalculate parent order total when an item is removed
        order.update_total_amount()

    def __str__(self):
        return f"{self.quantity}x {self.product.sku} for {self.order.order_number}"