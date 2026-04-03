"""CLI commands for the ingest pipeline."""

from __future__ import annotations

from pathlib import Path

import click

from ..util.logging import info, success, error, warn, status
from ..vault.frontmatter import write_frontmatter, read_frontmatter
from ..vault.paths import RAW_ARTICLES, RAW_PAPERS, RAW_REPOS, RAW_INDEX, slug


@click.group()
def ingest():
    """Ingest raw documents into the vault."""
    pass


@ingest.command("url")
@click.argument("url")
@click.option("--no-images", is_flag=True, help="Skip downloading images.")
@click.pass_context
def ingest_url(ctx: click.Context, url: str, no_images: bool) -> None:
    """Ingest a web article by URL."""
    from .web import fetch_article
    from .image import download_images, rewrite_image_urls
    from .metadata import create_raw_metadata, update_raw_index

    vault_root: Path = ctx.obj["vault_root"]
    config = ctx.obj["config"]

    with status(f"Fetching {url}..."):
        title, markdown, image_urls = fetch_article(url)

    info(f"Fetched: {title}")

    doc_slug = slug(title)
    rel_path = f"{RAW_ARTICLES}/{doc_slug}.md"

    # Download images
    if not no_images and image_urls and config.ingest.download_images:
        with status(f"Downloading {len(image_urls)} images..."):
            url_map = download_images(image_urls, vault_root, doc_slug)
            markdown = rewrite_image_urls(markdown, url_map)
        success(f"Downloaded {len(url_map)} images")

    # Create frontmatter and write
    meta = create_raw_metadata(
        source_type="web_article",
        title=title,
        content=markdown,
        source_url=url,
    )
    write_frontmatter(vault_root / rel_path, meta, markdown)

    # Update raw index
    update_raw_index(vault_root, rel_path, meta)

    success(f"Ingested: {rel_path}")


@ingest.command("file")
@click.argument("filepath", type=click.Path(exists=True))
@click.pass_context
def ingest_file(ctx: click.Context, filepath: str) -> None:
    """Ingest a local file (markdown, PDF, image)."""
    from .metadata import create_raw_metadata, update_raw_index

    vault_root: Path = ctx.obj["vault_root"]
    source = Path(filepath)
    suffix = source.suffix.lower()

    if suffix == ".pdf":
        from .pdf import extract_pdf_text

        with status(f"Extracting text from {source.name}..."):
            title, content = extract_pdf_text(source)

        doc_slug = slug(title)
        rel_path = f"{RAW_PAPERS}/{doc_slug}.md"
        meta = create_raw_metadata(
            source_type="pdf", title=title, content=content
        )
        write_frontmatter(vault_root / rel_path, meta, content)

    elif suffix in {".md", ".markdown", ".txt"}:
        content = source.read_text(encoding="utf-8")
        title = source.stem.replace("-", " ").replace("_", " ").title()

        # Try to extract title from content
        for line in content.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        doc_slug = slug(title)
        rel_path = f"{RAW_ARTICLES}/{doc_slug}.md"
        meta = create_raw_metadata(
            source_type="markdown", title=title, content=content
        )
        write_frontmatter(vault_root / rel_path, meta, content)

    elif suffix in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}:
        import shutil

        doc_slug = slug(source.stem)
        dest = vault_root / "raw" / "images" / source.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        rel_path = f"raw/images/{source.name}"

        meta = create_raw_metadata(
            source_type="image", title=source.stem, content=""
        )
        # No frontmatter for images, just update index
        update_raw_index(vault_root, rel_path, meta)
        success(f"Ingested image: {rel_path}")
        return

    else:
        error(f"Unsupported file type: {suffix}")
        return

    update_raw_index(vault_root, rel_path, meta)
    success(f"Ingested: {rel_path}")


@ingest.command("repo")
@click.argument("repo_url")
@click.pass_context
def ingest_repo(ctx: click.Context, repo_url: str) -> None:
    """Ingest a git repository."""
    from .repo import summarize_repo
    from .metadata import create_raw_metadata, update_raw_index

    vault_root: Path = ctx.obj["vault_root"]

    with status(f"Cloning and summarizing {repo_url}..."):
        title, content = summarize_repo(repo_url)

    doc_slug = slug(title)
    rel_path = f"{RAW_REPOS}/{doc_slug}.md"

    meta = create_raw_metadata(
        source_type="repo", title=title, content=content, source_url=repo_url
    )
    write_frontmatter(vault_root / rel_path, meta, content)
    update_raw_index(vault_root, rel_path, meta)

    success(f"Ingested repo: {rel_path}")


@ingest.command("dir")
@click.argument("directory", type=click.Path(exists=True))
@click.pass_context
def ingest_dir(ctx: click.Context, directory: str) -> None:
    """Ingest all supported files from a directory."""
    source_dir = Path(directory)
    supported = {".md", ".markdown", ".txt", ".pdf", ".png", ".jpg", ".jpeg", ".gif"}

    files = [f for f in source_dir.rglob("*") if f.is_file() and f.suffix.lower() in supported]

    if not files:
        warn(f"No supported files found in {directory}")
        return

    info(f"Found {len(files)} files to ingest")
    for f in files:
        ctx.invoke(ingest_file, filepath=str(f))


@ingest.command("list")
@click.pass_context
def ingest_list(ctx: click.Context) -> None:
    """List all ingested raw documents."""
    from rich.table import Table
    from ..util.logging import console

    vault_root: Path = ctx.obj["vault_root"]
    index_path = vault_root / RAW_INDEX

    if not index_path.exists():
        warn("No raw index found. Run 'wiki init' first.")
        return

    meta, _ = read_frontmatter(index_path)
    docs = meta.get("documents", [])

    if not docs:
        info("No documents ingested yet.")
        return

    table = Table(title="Raw Documents")
    table.add_column("Status", style="bold")
    table.add_column("Type")
    table.add_column("Title")
    table.add_column("Path")

    for doc in docs:
        status_style = "green" if doc.get("status") == "compiled" else "yellow"
        table.add_row(
            f"[{status_style}]{doc.get('status', '?')}[/{status_style}]",
            doc.get("source_type", "?"),
            doc.get("title", "?"),
            doc.get("path", "?"),
        )

    console.print(table)
