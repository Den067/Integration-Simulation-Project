
import os
import uuid
import django
from django.conf import settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "integration.settings")
django.setup()

from payments.service import initiate_payment
from payments.models import PaymentTransaction
from payments.onekhusa import OneKhusaError

suffix = uuid.uuid4().hex[:12].upper()
reference = "DEMO" + suffix

try:
    payment = initiate_payment(
        amount="100.00",
        reference_number=reference,
        captured_by=settings.ONEKHUSA_SANDBOX_USER_EMAIL,
        description="OneKhusa integration database test",
    )

    print("Local transaction saved.")
    print("Reference:", payment.reference_number)
    print("Status:", payment.status)
    print("TAN stored:", bool(payment.timed_account_number))
    print("Expiry:", payment.provider_expiry)

except (ValueError, OneKhusaError) as exc:
    print("Test did not complete:", exc)
    print("Check the database record for its resulting status.")

finally:
    print(
        "Matching local records:",
        PaymentTransaction.objects.filter(
            reference_number=reference
        ).count(),
    )
