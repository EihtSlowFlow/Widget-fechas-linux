"""Validación compartida de enlaces de clases virtuales."""

from urllib.parse import urlsplit


def is_valid_virtual_class_url(url: object) -> bool:
    """Acepta únicamente URLs HTTP(S) absolutas y sin espacios de control."""
    if not isinstance(url, str) or not url or url != url.strip():
        return False
    if any(char.isspace() or ord(char) < 32 for char in url):
        return False

    try:
        parsed = urlsplit(url)
        # Acceder a port también detecta puertos fuera de rango o no numéricos.
        parsed.port
    except ValueError:
        return False

    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.hostname)
