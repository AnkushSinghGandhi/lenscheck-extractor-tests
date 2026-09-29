from rest_framework import serializers
from apps.orders.models import Order


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order          # a .save() writes `orders`, not "OrderSerializer"
        fields = "__all__"
