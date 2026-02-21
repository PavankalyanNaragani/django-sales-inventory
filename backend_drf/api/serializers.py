from rest_framework import serializers
from django.db import transaction
from .models import Product, Inventory, Dealer, Order, OrderItem

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ['id', 'product', 'available_quantity', 'last_updated']
        read_only_fields = ['product']  

class ProductSerializer(serializers.ModelSerializer): 
    available_stock = serializers.IntegerField(source='inventory.available_quantity', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'sku', 'name', 'description', 'current_price', 'available_stock', 'created_at', 'updated_at']

    def create(self, validated_data):
        """
        When a product is created, automatically create its linked 1-to-1 Inventory record
        starting with 0 stock.
        """
        with transaction.atomic():
            product = Product.objects.create(**validated_data)
            Inventory.objects.create(product=product, available_quantity=0)
            return product

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'unit_price', 'line_total']
        read_only_fields = ['unit_price', 'line_total']

class OrderSerializer(serializers.ModelSerializer): 
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'dealer', 'status', 'total_amount', 'items', 'created_at', 'updated_at']
        # The user shouldn't be able to manually set these fields via the API
        read_only_fields = ['order_number', 'status', 'total_amount', 'created_at', 'updated_at']

    def create(self, validated_data):
        """
        Writable Nested Serializer: Handles creating a Draft order and its items in one request.
        """
        items_data = validated_data.pop('items')
        
        with transaction.atomic():
            # Orders are created as Draft by default in the model [cite: 73]
            order = Order.objects.create(**validated_data)
            
            for item_data in items_data:
                OrderItem.objects.create(order=order, **item_data)
                
            return order

    def update(self, instance, validated_data):
        """
        Writable Nested Serializer: Handles updating a Draft order's items[cite: 78].
        """
        if instance.status != 'Draft':
            raise serializers.ValidationError("Only Draft orders can be updated.")

        items_data = validated_data.pop('items', None)

        with transaction.atomic():
            instance.dealer = validated_data.get('dealer', instance.dealer)
            instance.save()

            if items_data is not None:
                instance.items.all().delete()
                for item_data in items_data:
                    OrderItem.objects.create(order=instance, **item_data)

            return instance

class DealerSerializer(serializers.ModelSerializer):
    # Fulfills requirement: "Get dealer details with orders" 
    # We use SerializerMethodField to prevent a massive nested payload if they have hundreds of orders
    recent_orders = serializers.SerializerMethodField()

    class Meta:
        model = Dealer
        fields = ['id', 'dealer_code', 'name', 'email', 'address', 'phone', 'recent_orders', 'created_at', 'updated_at']

    def get_recent_orders(self, obj):
        orders = obj.orders.all().order_by('-created_at')
        return [
            {
                "id": order.id,
                "order_number": order.order_number,
                "status": order.status,
                "total_amount": order.total_amount
            } for order in orders
        ]