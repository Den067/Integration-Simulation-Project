
import hashlib
import hmac
import json
from decimal import Decimal
from django.utils import timezone
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from payments.models import PaymentTransaction


class PaymentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/payments/initiate/"

        self.valid_payload = {
            "amount": "100.00",
            "reference_number": "TEST123456",
            "description": "Automated integration test",
        }
    
    @patch("payments.views.initiate_payment")
    def test_valid_request_returns_201(self, mock_initiate):
        from datetime import timedelta
        from django.utils import timezone

        # Return an unsaved model instance. The reference must not
        # already exist, or the serializer correctly rejects it.
        payment = PaymentTransaction(
            reference_number="TEST123456",
            amount=Decimal("100.00"),
            captured_by="sandbox-user@example.com",
            timed_account_number="12345678",
            provider_expiry=timezone.now() + timedelta(minutes=15),
            status=PaymentTransaction.Status.REQUESTED,
        )
        mock_initiate.return_value = payment

        response = self.client.post(
            self.url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "REQUESTED")
        self.assertTrue(response.data["timed_account_number"])
        mock_initiate.assert_called_once()


    @patch("payments.views.initiate_payment")
    def test_zero_amount_is_rejected(self, mock_initiate):
        payload = {
            **self.valid_payload,
            "amount": "0.00",
        }

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        mock_initiate.assert_not_called()

    @patch("payments.views.initiate_payment")
    def test_duplicate_reference_is_rejected(self, mock_initiate):
        PaymentTransaction.objects.create(
            reference_number="TEST123456",
            amount=Decimal("100.00"),
            captured_by="sandbox-user@example.com",
        )

        response = self.client.post(
            self.url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        mock_initiate.assert_not_called()

    @patch("payments.views.initiate_payment")
    def test_missing_description_is_rejected(self, mock_initiate):
        payload = {
            "amount": "100.00",
            "reference_number": "TEST123456",
        }

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        mock_initiate.assert_not_called()


@override_settings(ONEKHUSA_WEBHOOK_SECRET="test-webhook-secret")
class OneKhusaWebhookTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/payments/webhooks/onekhusa/"
        self.secret = "test-webhook-secret"

        self.payment = PaymentTransaction.objects.create(
            reference_number="HOOKTEST001",
            amount="100.00",
            captured_by="sandbox@example.com",
            status=PaymentTransaction.Status.REQUESTED,
        )

    def make_payload(self, event="payrequest.success"):
        return {
            "transactionAmount": "100.00",
            "transactionStatusCode": (
                "S" if event == "payrequest.success" else "R"
            ),
            "metaData": {
                "ReferenceNumber": self.payment.reference_number,
                "TimedAccountNumber": "12345678",
            },
        }

    def send_webhook(self, payload, event="payrequest.success",
                     valid_signature=True):
        body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            self.secret.encode("utf-8"),
            body,
            hashlib.sha512,
        ).hexdigest()

        if not valid_signature:
            signature = "invalid-signature"

        return self.client.generic(
            "POST",
            self.url,
            body,
            content_type="application/json",
            HTTP_X_ONEKHUSA_WEBHOOK_SIGNATURE=signature,
            HTTP_X_ONEKHUSA_WEBHOOK_EVENT=event,
        )

    def test_success_webhook_marks_payment_paid(self):
        response = self.send_webhook(self.make_payload())

        self.assertEqual(response.status_code, 200)

        self.payment.refresh_from_db()
        self.assertEqual(
            self.payment.status,
            PaymentTransaction.Status.PAID,
        )

    def test_invalid_signature_is_rejected(self):
        response = self.send_webhook(
            self.make_payload(),
            valid_signature=False,
        )

        self.assertEqual(response.status_code, 401)

        self.payment.refresh_from_db()
        self.assertEqual(
            self.payment.status,
            PaymentTransaction.Status.REQUESTED,
        )

    def test_duplicate_success_webhook_is_safe(self):
        first = self.send_webhook(self.make_payload())
        second = self.send_webhook(self.make_payload())

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        self.payment.refresh_from_db()
        self.assertEqual(
            self.payment.status,
            PaymentTransaction.Status.PAID,
        )

    def test_reversal_webhook_marks_paid_payment_reversed(self):
        self.payment.status = PaymentTransaction.Status.PAID
        self.payment.save(update_fields=["status", "updated_at"])

        response = self.send_webhook(
            self.make_payload("payrequest.reversed"),
            event="payrequest.reversed",
        )

        self.assertEqual(response.status_code, 200)

        self.payment.refresh_from_db()
        self.assertEqual(
            self.payment.status,
            PaymentTransaction.Status.REVERSED,
        )
