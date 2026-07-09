"""Infrastructure security adapters."""

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from app.application.security import PasswordHasher, TokenService


class PBKDF2PasswordHasher(PasswordHasher):
    """PBKDF2-HMAC password hasher using a per-password salt."""

    def __init__(self, iterations: int = 120_000):
        self.iterations = iterations

    def hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            self.iterations,
        ).hex()
        return f"pbkdf2_sha256${self.iterations}${salt}${digest}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations, salt, expected = password_hash.split("$", 3)
        except ValueError:
            return False

        if algorithm != "pbkdf2_sha256":
            return False

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(actual, expected)


class HMACTokenService(TokenService):
    """Stateless signed access tokens backed by HMAC-SHA256."""

    def __init__(
        self,
        secret: Optional[str] = None,
        expires_in: timedelta = timedelta(hours=8),
    ):
        self.secret = (
            secret
            or os.getenv("SINVEST_AUTH_SECRET")
            or "sinvest-development-secret"
        ).encode("utf-8")
        self.expires_in = expires_in

    def issue_token(self, user_id: str) -> str:
        expires_at = datetime.utcnow() + self.expires_in
        payload = {
            "sub": user_id,
            "exp": int(expires_at.timestamp()),
        }
        payload_bytes = json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        encoded_payload = self._base64url_encode(payload_bytes)
        signature = self._sign(encoded_payload)
        return f"{encoded_payload}.{signature}"

    def verify_token(self, token: str) -> Optional[str]:
        try:
            encoded_payload, signature = token.split(".", 1)
        except ValueError:
            return None

        expected_signature = self._sign(encoded_payload)
        if not hmac.compare_digest(signature, expected_signature):
            return None

        try:
            payload = json.loads(self._base64url_decode(encoded_payload))
        except (ValueError, json.JSONDecodeError):
            return None

        if int(payload.get("exp", 0)) < int(datetime.utcnow().timestamp()):
            return None

        user_id = payload.get("sub")
        return user_id if isinstance(user_id, str) and user_id else None

    def _sign(self, encoded_payload: str) -> str:
        signature = hmac.new(
            self.secret,
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return self._base64url_encode(signature)

    @staticmethod
    def _base64url_encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    @staticmethod
    def _base64url_decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)
