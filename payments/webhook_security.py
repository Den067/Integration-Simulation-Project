
import hashlib
import hmac


def verify_onekhusa_signature(raw_body, secret, supplied_signature):
    if not raw_body or not secret or not supplied_signature:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    return hmac.compare_digest(
        expected,
        supplied_signature.lower(),
    )
