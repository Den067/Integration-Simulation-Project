
import os
import uuid
import django
from datetime import datetime, timezone
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "integration.settings")
django.setup()

from payments.onekhusa import OneKhusaClient, OneKhusaError

# Sandbox test only. Use the background user's registered email.
captured_by = settings.ONEKHUSA_SANDBOX_USER_EMAIL

# Generate unique values for this test run.
suffix = uuid.uuid4().hex[:12].upper()
reference = "DEMO" + suffix
idempotency_key = str(uuid.uuid4())

try:
    result = OneKhusaClient().initiate_request_to_pay(
        amount="100.00",
        reference_number=reference,
        description="OneKhusa integration sandbox test",
        captured_by=captured_by,
        idempotency_key=idempotency_key,
    )

    print("Payment request accepted by OneKhusa.")
    print("Reference:", reference)
    print("TAN received:", bool(result["timed_account_number"]))
    print("Expiry:", result["expiry_date"])
    print("Expiry in minutes:", result["expiry_in_minutes"])
    print("Payment completed: No — awaiting customer payment.")

except OneKhusaError as exc:
    print("Payment initiation failed:", exc)
