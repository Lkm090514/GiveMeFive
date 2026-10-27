"""Password gate for the isolated GMF managed preview (not production SSO)."""
import hashlib
import hmac


def require_password(raw: str | None) -> str:
    """Refuse to expose a personal preview unless a nontrivial password is set."""
    if not isinstance(raw, str) or not (16 <= len(raw) <= 1024) or not raw.strip():
        raise RuntimeError('GMF_PREVIEW_PASSWORD must be set to a secret of at least 16 characters.')
    return raw


def matches(candidate: object, expected: str) -> bool:
    if not isinstance(candidate, str) or len(candidate) > 1024:
        return False
    # Compare fixed-length digests to avoid revealing password length via timing.
    return hmac.compare_digest(hashlib.sha256(candidate.encode('utf-8')).digest(), hashlib.sha256(expected.encode('utf-8')).digest())
