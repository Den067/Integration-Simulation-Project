
from decimal import Decimal
from django.utils import timezone
from unittest.mock import patch

from django.test import TestCase
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
