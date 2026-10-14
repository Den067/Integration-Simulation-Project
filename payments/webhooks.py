
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction as db_transaction
from django.http import HttpResponse

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import PaymentTransaction
from payments.webhook_security import verify_onekhusa_signature


class OneKhusaWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        signature = request.headers.get(
            "X-OneKhusa-Webhook-Signature", ""
        )
        event = request.headers.get(
            "X-OneKhusa-Webhook-Event", ""
        )

        secret = settings.ONEKHUSA_WEBHOOK_SECRET
        if not secret:
            return Response(
                {"detail": "Webhook secret is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not verify_onekhusa_signature(
            request.body, secret, signature
        ):
            return Response(
                {"detail": "Invalid webhook signature."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if event not in {
            "payrequest.success",
            "payrequest.reversed",
        }:
            return Response(
                {"detail": "Unsupported webhook event."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = request.data
        metadata = payload.get("metaData") or {}
        reference = metadata.get("referenceNumber")

        if not reference:
            return Response(
                {"detail": "Missing transaction reference."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = Decimal(str(payload["transactionAmount"]))
        except (KeyError, InvalidOperation, ValueError):
            return Response(
                {"detail": "Invalid transaction amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not amount.is_finite() or amount <= 0:
            return Response(
                {"detail": "Invalid transaction amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expected_code = (
            "S" if event == "payrequest.success" else "R"
        )
        if payload.get("transactionStatusCode") != expected_code:
            return Response(
                {"detail": "Unexpected transaction status code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with db_transaction.atomic():
            payment = (
                PaymentTransaction.objects.select_for_update()
                .filter(reference_number=reference)
                .first()
            )

            if payment is None:
                return Response(
                    {"detail": "Transaction not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if payment.amount != amount:
                return Response(
                    {"detail": "Transaction amount mismatch."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if event == "payrequest.success":
                if payment.status == PaymentTransaction.Status.REVERSED:
                    return Response(
                        {"detail": "Transaction is already reversed."},
                        status=status.HTTP_409_CONFLICT,
                    )
                payment.status = PaymentTransaction.Status.PAID
            else:
                if payment.status != PaymentTransaction.Status.PAID:
                    return Response(
                        {"detail": "Only a paid transaction can be reversed."},
                        status=status.HTTP_409_CONFLICT,
                    )
                payment.status = PaymentTransaction.Status.REVERSED

            payment.save(update_fields=["status", "updated_at"])

        return HttpResponse("acknowledged", status=200)
