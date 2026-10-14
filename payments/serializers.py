
from decimal import Decimal

from rest_framework import serializers


class PaymentRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    reference_number = serializers.CharField(
        min_length=5,
        max_length=25,
        trim_whitespace=True,
    )

    description = serializers.CharField(
        max_length=200,
        trim_whitespace=True,
    )

    def validate_reference_number(self, value):
        from payments.models import PaymentTransaction

        if PaymentTransaction.objects.filter(
            reference_number=value
        ).exists():
            raise serializers.ValidationError(
                "This transaction reference already exists."
            )

        return value
