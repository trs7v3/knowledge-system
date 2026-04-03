"""PDF text extraction."""

from __future__ import annotations

from pathlib import Path


def extract_pdf_text(pdf_path: Path) -> tuple[str, str]:
    """Extract text content from a PDF file.

    Returns:
        (title, markdown_content)
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber is required for PDF ingestion. "
            "Install it with: pip install pdfplumber"
        )

    text_parts = []
    title = ""

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            if i == 0 and not title:
                # Use first non-empty line as title
                for line in page_text.splitlines():
                    line = line.strip()
                    if line and len(line) > 3:
                        title = line
                        break
            text_parts.append(page_text)

    if not title:
        title = pdf_path.stem.replace("-", " ").replace("_", " ").title()

    # Join pages with double newlines
    content = "\n\n---\n\n".join(text_parts)

    return title, content
