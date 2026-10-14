
import requests
from django.conf import settings


class OneKhusaError(Exception):
    """OneKhusa integration error."""

    def __init__(self, message, outcome_unknown=False):
        super().__init__(message)
        self.outcome_unknown = outcome_unknown


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


    
    def initiate_request_to_pay(
        self,
        amount,
        reference_number,
        description,
        captured_by,
        idempotency_key,
    ):
        from decimal import Decimal, InvalidOperation

        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            raise OneKhusaError("Invalid transaction amount.")

        if not amount.is_finite() or amount <= 0:
            raise OneKhusaError(
                "Transaction amount must be greater than zero."
            )

        if not reference_number or not (
            5 <= len(reference_number) <= 25
        ):
            raise OneKhusaError(
                "Reference must contain 5 to 25 characters."
            )

        if not idempotency_key or not idempotency_key.strip():
            raise OneKhusaError("Idempotency key is required.")

        token_data = self.get_access_token()
        token = token_data["access_token"]

        url = f"{self.base_url}/collections/requestToPay/initiate"

        payload = {
            "merchantAccountNumber": int(
                self.merchant_account_number
            ),
            "transactionAmount": float(amount),
            "transactionDescription": description,
            "referenceNumber": reference_number,
            "capturedBy": captured_by,
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept-Language": "en",
            "X-Idempotency-Key": idempotency_key,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=20,
            )
        except requests.Timeout as exc:
            raise OneKhusaError(
                "Payment request timed out; outcome requires reconciliation.",
                outcome_unknown=True,
            ) from exc
        except requests.RequestException as exc:
            raise OneKhusaError(
                "Payment request encountered a network error; "
                "outcome requires reconciliation.",
                outcome_unknown=True,
            ) from exc

        if not response.ok:
            raise OneKhusaError(
                f"Payment initiation failed with HTTP "
                f"{response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise OneKhusaError(
                "OneKhusa returned invalid JSON."
            ) from exc

        required_fields = (
            "timedAccountNumber",
            "expiryDate",
            "expiryInMinutes",
        )

        if any(field not in data for field in required_fields):
            raise OneKhusaError(
                "Response is missing expected payment details."
            )

        return {
            "merchant_account_number": data.get(
                "merchantAccountNumber"
            ),
            "timed_account_number": data["timedAccountNumber"],
            "expiry_date": data["expiryDate"],
            "expiry_in_minutes": data["expiryInMinutes"],
        }
