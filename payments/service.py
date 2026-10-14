
from datetime import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from payments.models import PaymentTransaction
from payments.onekhusa import OneKhusaClient, OneKhusaError


def initiate_payment(
    *,
    amount,
    reference_number,
    captured_by,
    description,
):
    amount = Decimal(str(amount))

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    if not reference_number or not 5 <= len(reference_number) <= 25:
        raise ValueError("Reference must contain 5 to 25 characters.")

    # Save the local record before contacting the provider.
    try:
        with transaction.atomic():
            payment = PaymentTransaction.objects.create(
                amount=amount,
                reference_number=reference_number,
                captured_by=captured_by,
            )
    except IntegrityError as exc:
        raise ValueError(
            "This transaction reference already exists."
        ) from exc

    client = OneKhusaClient()

    try:
        result = client.initiate_request_to_pay(
            amount=payment.amount,
            reference_number=payment.reference_number,
            description=description,
            captured_by=payment.captured_by,
            idempotency_key=str(payment.idempotency_key),
        )

    except OneKhusaError as exc:
        payment.status = (
            PaymentTransaction.Status.UNKNOWN
            if exc.outcome_unknown
            else PaymentTransaction.Status.FAILED
        )
        payment.last_error = str(exc)[:250]
        payment.save(update_fields=[
            "status", "last_error", "updated_at"
        ])
        raise

    expiry_value = result["expiry_date"]

    try:
        expiry = datetime.fromisoformat(
            expiry_value.replace("Z", "+00:00")
        )
        if timezone.is_naive(expiry):
            expiry = timezone.make_aware(expiry)
    except (ValueError, TypeError, AttributeError) as exc:
        payment.status = PaymentTransaction.Status.UNKNOWN
        payment.last_error = (
            "Provider accepted the request, but its expiry "
            "could not be parsed."
        )
        payment.save(update_fields=[
            "status", "last_error", "updated_at"
        ])
        raise OneKhusaError(
            payment.last_error,
            outcome_unknown=True,
        ) from exc

    payment.timed_account_number = str(
        result["timed_account_number"]
    )
    payment.provider_expiry = expiry
    payment.status = PaymentTransaction.Status.REQUESTED
    payment.last_error = ""
    payment.save(update_fields=[
        "timed_account_number",
        "provider_expiry",
        "status",
        "last_error",
        "updated_at",
    ])

    return payment
