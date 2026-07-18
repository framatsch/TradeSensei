"""OAuth helper utilities shared across broker integrations."""

from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import urlparse

from app.core.exceptions import ConfigurationError


def generate_pkce_verifier(length: int = 64) -> str:
    """Generate a URL-safe PKCE code verifier string."""
    if length < 43 or length > 128:
        raise ValueError("PKCE verifier length must be between 43 and 128.")
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_pkce_challenge(verifier: str) -> str:
    """Generate the PKCE S256 challenge from a verifier."""
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def generate_oauth_state(bytes_len: int = 24) -> str:
    """Generate a random URL-safe OAuth state token."""
    return secrets.token_urlsafe(bytes_len)


def is_loopback_redirect_uri(uri: str) -> bool:
    """Return True when URI points to localhost/127.0.0.1 loopback."""
    parsed = urlparse(uri)
    host = (parsed.hostname or "").lower()
    return host in {"127.0.0.1", "localhost"}


def validate_schwab_oauth_mode_redirect(mode: str, redirect_uri: str) -> None:
    """Validate Schwab OAuth mode and redirect-uri consistency."""
    parsed = urlparse(redirect_uri)
    if parsed.scheme.lower() != "https":
        raise ConfigurationError("Schwab redirect URI must use https.")

    loopback = is_loopback_redirect_uri(redirect_uri)
    if mode == "paste" and not loopback:
        raise ConfigurationError("SCHWAB_OAUTH_MODE=paste requires a loopback redirect URI (https://127.0.0.1 or https://localhost).")
    if mode == "callback" and loopback:
        raise ConfigurationError("SCHWAB_OAUTH_MODE=callback requires a non-loopback TLS redirect URI.")
