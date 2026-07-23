import base64
import hashlib
import hmac

from app.security import verify_line_signature


def test_verify_line_signature_accepts_valid_signature() -> None:
    body = b'{"events":[]}'
    signature = base64.b64encode(hmac.new(b"secret", body, hashlib.sha256).digest()).decode()

    assert verify_line_signature(body, signature, "secret")


def test_verify_line_signature_rejects_invalid_signature() -> None:
    assert not verify_line_signature(b'{"events":[]}', "invalid", "secret")
