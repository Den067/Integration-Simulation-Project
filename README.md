# OneKhusa Payment Integration Simulation

## Overview

A Django REST Framework integration with the OneKhusa sandbox for initiating mobile money payment requests, storing transaction records, and processing payment-status webhooks.

## Features

- Sandbox API authentication with environment-based credentials.
- Request-to-pay initiation through a Django REST API.
- Database persistence of transaction references, amounts, status, TAN, and expiry where provided.
- Webhook signature verification using HMAC-SHA512.
- Payment status updates from `REQUESTED` to `PAID`.
- Reversal handling and duplicate-delivery checks.
- Input validation and handling of provider errors and uncertain outcomes.
- Automated tests for API validation and webhook processing.

## Technology Stack

- Python
- Django
- Django REST Framework
- SQLite for local development
- Requests
- OneKhusa sandbox API

## Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies:

   `pip install -r requirements.txt`

4. Create a `.env` file based on `.env.example`.
5. Add your own sandbox credentials and webhook secret to `.env`.
6. Apply migrations:

   `python manage.py migrate`

7. Start the development server:

   `python manage.py runserver`


## Testing

Run the automated tests:

`python manage.py test`

The verified test suite currently contains eight passing tests.

## Payment Flow

1. The client submits a payment request.
2. The application validates the request and records the local transaction.
3. The application requests payment initiation from OneKhusa.
4. The customer completes the payment through the sandbox simulation.
5. OneKhusa sends a webhook to the configured endpoint.
6. The application verifies the webhook signature and validates the transaction.
7. The matching local transaction is updated to `PAID` or, when a valid reversal is received, `REVERSED`.

## Verification

The sandbox payment flow was manually tested. Payment initiation returned HTTP 201, the webhook was acknowledged with HTTP 200, and the matching database transaction changed from `REQUESTED` to `PAID`.

Automated tests passed for the current eight-test suite.

## Scope and Limitations

This is a sandbox integration and learning project, not a production payment service. Production deployment would require additional security, monitoring, concurrency, deployment, and operational reviews.

## Security

- Credentials and webhook secrets are supplied through environment variables.
- Webhook signatures are verified before processing events.
- Transaction references and amounts are checked before changing payment status.
- No real-money settlement is claimed by this sandbox demonstration.
