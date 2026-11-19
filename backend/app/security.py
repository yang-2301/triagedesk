"""JWT issuing/verification and PBKDF2 password hashing (stdlib only)."""
import datetime
import hashlib
import hmac
import secrets

import jwt

from .config import SECRET_KEY, ACCESS_TOKEN_TTL_MIN, REFRESH_TOKEN_TTL_DAYS

_PBKDF2_ITERATIONS = 240_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(),
                                 _PBKDF2_ITERATIONS).hex()
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(),
                                        int(iterations)).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


def _make_token(user_id: str, role: str, kind: str, ttl: datetime.timedelta) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": user_id, "role": role, "typ": kind,
        "iat": now, "exp": now + ttl,
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def make_access_token(user_id: str, role: str) -> str:
    return _make_token(user_id, role, "access",
                       datetime.timedelta(minutes=ACCESS_TOKEN_TTL_MIN))


def make_refresh_token(user_id: str, role: str) -> str:
    return _make_token(user_id, role, "refresh",
                       datetime.timedelta(days=REFRESH_TOKEN_TTL_DAYS))


class AuthError(Exception):
    """Raised when a token is invalid, expired, or of the wrong type."""


def decode_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("invalid token") from exc
    if payload.get("typ") != expected_type:
        raise AuthError(f"expected {expected_type} token")
    return payload
