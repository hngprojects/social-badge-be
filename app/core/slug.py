"""Share slug generator for organiser templates."""

import secrets
import string

SLUG_LENGTH = 12
SLUG_ALPHABET = string.ascii_letters + string.digits


def generate_share_slug(length: int = SLUG_LENGTH) -> str:
    """Generate a URL-safe base62 random slug.

    Uses secrets.choice for cryptographic randomness.
    """
    return "".join(secrets.choice(SLUG_ALPHABET) for _ in range(length))
