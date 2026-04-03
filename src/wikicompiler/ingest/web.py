"""Web article fetching and conversion to markdown."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


def fetch_article(url: str) -> tuple[str, str, list[str]]:
    """Fetch a web article and convert to markdown.

    Returns:
        (title, markdown_content, image_urls)
    """
    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; WikiCompiler/0.1)",
        },
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract title
    title = _extract_title(soup)

    # Remove unwanted elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Find the main content area
    content_elem = _find_content(soup)

    # Extract image URLs before conversion
    image_urls = _extract_image_urls(content_elem, url)

    # Convert to markdown
    markdown = md(
        str(content_elem),
        heading_style="ATX",
        bullets="-",
        strip=["img"],  # We'll handle images separately
    )

    # Clean up the markdown
    markdown = _clean_markdown(markdown)

    return title, markdown, image_urls


def _extract_title(soup: BeautifulSoup) -> str:
    """Extract the best title from the page."""
    # Try og:title first
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    # Try <title> tag
    if soup.title and soup.title.string:
        return soup.title.string.strip()

    # Try first h1
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    return "Untitled"


def _find_content(soup: BeautifulSoup) -> BeautifulSoup:
    """Find the main content element of the page."""
    # Try common content selectors
    for selector in ["article", "main", '[role="main"]', ".post-content", ".entry-content", ".article-content"]:
        elem = soup.select_one(selector)
        if elem:
            return elem

    # Fallback to body
    return soup.find("body") or soup


def _extract_image_urls(elem: BeautifulSoup, base_url: str) -> list[str]:
    """Extract all image URLs from the content."""
    urls = []
    for img in elem.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if src:
            absolute_url = urljoin(base_url, src)
            if _is_valid_image_url(absolute_url):
                urls.append(absolute_url)
    return urls


def _is_valid_image_url(url: str) -> bool:
    """Check if URL looks like a valid image."""
    parsed = urlparse(url)
    if not parsed.scheme.startswith("http"):
        return False
    path = parsed.path.lower()
    return any(path.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"])


def _clean_markdown(text: str) -> str:
    """Clean up converted markdown."""
    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove trailing whitespace on lines
    text = "\n".join(line.rstrip() for line in text.splitlines())
    # Strip leading/trailing whitespace
    text = text.strip()
    return text
