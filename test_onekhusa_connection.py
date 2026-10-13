
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "integration.settings")
django.setup()

from payments.onekhusa import OneKhusaClient, OneKhusaError

try:
    result = OneKhusaClient().get_access_token()

    print("Authentication successful.")
    print("Token received: Yes")
    print("Expiry (minutes):", result["expiry_in_minutes"])

except OneKhusaError as exc:
    print("Authentication test failed:", exc)
