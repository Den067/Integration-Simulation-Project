
import requests
from django.conf import settings


class OneKhusaError(Exception):
    """Raised when communication with OneKhusa fails."""


class OneKhusaClient:
    def __init__(self):
        self.base_url = settings.ONEKHUSA_BASE_URL.rstrip("/")

        self.api_key = settings.ONEKHUSA_API_KEY
        self.api_secret = settings.ONEKHUSA_API_SECRET
        self.organisation_id = settings.ONEKHUSA_ORGANISATION_ID
        self.merchant_account_number = (
            settings.ONEKHUSA_MERCHANT_ACCOUNT_NUMBER
        )

    def get_access_token(self):
        required = {
            "API key": self.api_key,
            "API secret": self.api_secret,
            "Organisation ID": self.organisation_id,
            "Merchant Account Number": self.merchant_account_number,
        }

        missing = [
            name for name, value in required.items()
            if not value or not value.strip()
        ]

        if missing:
            raise OneKhusaError(
                "Missing configuration: " + ", ".join(missing)
            )

        url = f"{self.base_url}/account/getAccessToken"

        payload = {
            "apiKey": self.api_key,
            "apiSecret": self.api_secret,
            "organisationId": self.organisation_id,
            "merchantAccountNumber": int(self.merchant_account_number),
        }

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=15,
            )
        except requests.Timeout as exc:
            raise OneKhusaError(
                "OneKhusa authentication request timed out."
            ) from exc
        except requests.RequestException as exc:
            raise OneKhusaError(
                "Could not communicate with OneKhusa."
            ) from exc

        if not response.ok:
            raise OneKhusaError(
                f"OneKhusa authentication failed with HTTP "
                f"{response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise OneKhusaError(
                "OneKhusa returned an invalid JSON response."
            ) from exc

        token = data.get("accessToken")

        if not isinstance(token, str) or not token:
            raise OneKhusaError(
                "Authentication response did not contain an access token."
            )

        return {
            "access_token": token,
            "expires_on": data.get("expiresOn"),
            "expiry_in_minutes": data.get("expiryInMinutes"),
        }
