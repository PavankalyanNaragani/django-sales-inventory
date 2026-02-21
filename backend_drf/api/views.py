from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Order, Inventory
from .models import Product, Dealer, Inventory
from .serializers import ProductSerializer, DealerSerializer, InventorySerializer, OrderSerializer
from rest_framework.permissions import IsAdminUser
from .serializers import InventorySerializer
from django.db.models import Sum, Count

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    def update(self, request, *args, **kwargs):
        """Enforce Order Editing Rules: Only Draft orders can be updated."""
        order = self.get_object()
        if order.status != 'Draft':
            return Response(
                {"error": "Confirmed or Delivered orders cannot be modified."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Bonus: Deleting a confirmed order restores stock."""
        order = self.get_object()
        if order.status == 'Confirmed':
            with transaction.atomic():
                for item in order.items.all():
                    inventory = Inventory.objects.select_for_update().get(product=item.product)
                    inventory.available_quantity += item.quantity
                    inventory.save()
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        Confirms the order, validates stock, and deducts inventory.
        Uses atomic transactions to prevent race conditions.
        """
        order = self.get_object()

        # 1. Status Flow Validation
        if order.status != 'Draft':
            return Response(
                {"error": f"Invalid transition. Cannot change {order.status} order to Confirmed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Atomic Transaction for Stock Validation & Deduction
        try:
            with transaction.atomic():
                items = order.items.select_related('product').all()
                
                if not items.exists():
                    return Response(
                        {"error": "Cannot confirm an order with no items."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                errors = []
                inventories_to_update = []

                for item in items:
                    # select_for_update() locks the database row until the transaction completes.
                    # This completely eliminates race conditions if multiple people order at once.
                    inventory = Inventory.objects.select_for_update().get(product=item.product)

                    # Check if requested quantity <= available stock
                    if item.quantity > inventory.available_quantity:
                        errors.append(
                            f"Insufficient stock for {item.product.name}. Available: {inventory.available_quantity}, Requested: {item.quantity}"
                        )
                    else:
                        # Deduct stock
                        inventory.available_quantity -= item.quantity
                        inventories_to_update.append(inventory)

                # 3. Reject Entire Order if ANY item fails validation
                if errors:
                    raise ValidationError({"errors": errors})

                for inv in inventories_to_update:
                    inv.save()

                order.status = 'Confirmed'
                order.save(update_fields=['status'])

        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {"message": "Order confirmed successfully.", "order_number": order.order_number},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def deliver(self, request, pk=None):
        """Marks a Confirmed order as Delivered."""
        order = self.get_object()

        if order.status != 'Confirmed':
            return Response(
                {"error": f"Invalid transition. Only 'Confirmed' orders can be marked 'Delivered'. Current status is '{order.status}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'Delivered'
        order.save(update_fields=['status'])
        
        return Response({"message": "Order marked as delivered."}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Order Summary/Report Endpoint
        Returns key metrics like total revenue and order counts by status.
        """
        total_orders = Order.objects.count()

        revenue_data = Order.objects.filter(
            status__in=['Confirmed', 'Delivered']
        ).aggregate(total_revenue=Sum('total_amount'))
        
        # If there are no orders yet, Sum returns None, so we default to 0.00
        total_revenue = revenue_data['total_revenue'] or 0.00
        status_counts = Order.objects.values('status').annotate(count=Count('id'))

        status_breakdown = {item['status']: item['count'] for item in status_counts}

        report = {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "status_breakdown": status_breakdown
        }

        return Response(report, status=status.HTTP_200_OK)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class DealerViewSet(viewsets.ModelViewSet):
    queryset = Dealer.objects.all()
    serializer_class = DealerSerializer



# Inherit from GenericViewSet and only add List (GET) and Update (PUT/PATCH) mixins
class InventoryViewSet(mixins.ListModelMixin, 
                       mixins.UpdateModelMixin, 
                       viewsets.GenericViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    lookup_field = 'product'
    lookup_url_kwarg = 'product_id' 
    permission_classes = [IsAdminUser]