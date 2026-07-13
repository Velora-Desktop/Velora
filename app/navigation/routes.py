from urllib.parse import urlparse


CATALOG_SCHEME = "velora"


def catalog_uri(catalog_id: str) -> str:
    return f"{CATALOG_SCHEME}://catalog/{catalog_id}"


def parse_catalog_uri(uri: str) -> str | None:
    parsed = urlparse(uri)
    if parsed.scheme != CATALOG_SCHEME or parsed.netloc != "catalog":
        return None
    catalog_id = parsed.path.strip("/")
    return catalog_id or None
