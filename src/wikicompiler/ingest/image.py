"""Image downloading and path rewriting for ingested documents."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import requests

from ..vault.paths import ASSETS_DIR, slug


def download_images(
    image_urls: list[str], vault_root: Path, doc_slug: str
) -> dict[str, str]:
    """Download images and return mapping of original_url -> local_relative_path.

    Images are saved to vault/assets/<doc_slug>/<filename>.
    """
    assets_dir = vault_root / ASSETS_DIR / doc_slug
    assets_dir.mkdir(parents=True, exist_ok=True)

    url_map: dict[str, str] = {}

    for i, url in enumerate(image_urls):
        try:
            filename = _url_to_filename(url, i)
            local_path = assets_dir / filename

            response = requests.get(url, timeout=15, stream=True)
            response.raise_for_status()

            # Enforce max file size (10 MB) to prevent abuse
            max_size = 10 * 1024 * 1024
            size = 0
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    size += len(chunk)
                    if size > max_size:
                        break
                    f.write(chunk)

            if size > max_size:
                local_path.unlink(missing_ok=True)
                continue

            # Validate the file is actually an image (check magic bytes)
            if not _is_valid_image_file(local_path):
                local_path.unlink(missing_ok=True)
                continue

            # Relative path from vault root
            rel_path = f"{ASSETS_DIR}/{doc_slug}/{filename}"
            url_map[url] = rel_path

        except (requests.RequestException, OSError):
            # Skip failed downloads silently
            continue

    return url_map


def rewrite_image_urls(markdown: str, url_map: dict[str, str]) -> str:
    """Replace remote image URLs in markdown with local paths."""
    for original_url, local_path in url_map.items():
        # Replace in markdown image syntax ![alt](url)
        markdown = markdown.replace(original_url, local_path)
    return markdown


def _is_valid_image_file(path: Path) -> bool:
    """Check if a file is a valid image by inspecting magic bytes."""
    try:
        header = path.read_bytes()[:16]
    except OSError:
        return False

    # PNG: \x89PNG\r\n\x1a\n
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    # JPEG: \xff\xd8\xff
    if header[:3] == b"\xff\xd8\xff":
        return True
    # GIF: GIF87a or GIF89a
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return True
    # WebP: RIFF....WEBP
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return True
    # SVG: starts with < (XML-based, check for svg tag)
    if header.lstrip()[:1] == b"<":
        # Read more to find <svg
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:500]
            return "<svg" in text.lower()
        except OSError:
            return False
    return False


def _url_to_filename(url: str, index: int) -> str:
    """Generate a local filename from an image URL."""
    parsed = urlparse(url)
    path = parsed.path
    # Get extension
    ext = Path(path).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}:
        ext = ".png"
    # Get a name from the URL path
    name = Path(path).stem
    if not name or len(name) > 60:
        name = f"image-{index}"
    name = slug(name)
    return f"{name}{ext}"
