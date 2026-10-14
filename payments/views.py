
from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import PaymentTransaction
from payments.onekhusa import OneKhusaError
from payments.serializers import PaymentRequestSerializer
from payments.service import initiate_payment


class PaymentInitiateView(APIView):
    def post(self, request):
        serializer = PaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not settings.ONEKHUSA_SANDBOX_USER_EMAIL:
            return Response(
                {"detail": "Payment integration is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            payment = initiate_payment(
                amount=serializer.validated_data["amount"],
                reference_number=serializer.validated_data[
                    "reference_number"
                ],
                captured_by=settings.ONEKHUSA_SANDBOX_USER_EMAIL,
                description=serializer.validated_data["description"],
            )

        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OneKhusaError as exc:
            current = PaymentTransaction.objects.get(
                reference_number=serializer.validated_data[
                    "reference_number"
                ]
            )

            response_status = (
                status.HTTP_202_ACCEPTED
                if current.status == PaymentTransaction.Status.UNKNOWN
                else status.HTTP_502_BAD_GATEWAY
            )

            return Response(
                {
                    "reference_number": current.reference_number,
                    "status": current.status,
                    "detail": str(exc),
                },
                status=response_status,
            )

        return Response(
            {
                "reference_number": payment.reference_number,
                "amount": str(payment.amount),
                "status": payment.status,
                "timed_account_number": payment.timed_account_number,
                "expiry": payment.provider_expiry.isoformat(),
                "message": (
                    "Payment request created. "
                    "Payment is not yet confirmed."
                ),
            },
            status=status.HTTP_201_CREATED,
        )
