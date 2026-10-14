from django.urls import path

from payments.views import PaymentInitiateView
from payments.webhooks import OneKhusaWebhookView

urlpatterns = [
    path(
        "initiate/",
        PaymentInitiateView.as_view(),
        name="payment-initiate",
    ), 
    path(
        "webhooks/onekhusa/",
        OneKhusaWebhookView.as_view(),
        name="onekhusa-webhook",
    ),
]