
import uuid

from django.db import models


class PaymentTransaction(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Payment Requested"
        REVERSED = "REVERSED", "Reversed"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        EXPIRED = "EXPIRED", "Expired"
        UNKNOWN = "UNKNOWN", "Outcome Unknown"

    reference_number = models.CharField(
        max_length=25,
        unique=True,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    captured_by = models.EmailField()

    idempotency_key = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.REQUESTED,
    )

    timed_account_number = models.CharField(
        max_length=100,
        blank=True,
    )
    provider_expiry = models.DateTimeField(
        null=True,
        blank=True,
    )
    last_error = models.CharField(
        max_length=250,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.reference_number} - {self.status}"
