"""Top-level CLI entry point for the wiki compiler."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import click
from rich.table import Table

from .util.config import load_config, write_default_config
from .util.logging import console, info, success, error
from .vault.frontmatter import write_frontmatter
from .vault.obsidian import init_obsidian_config
from .vault.paths import (
    WIKI_CATEGORIES,
    WIKI_DIR,
    RAW_DIR,
    OUTPUT_DIR,
    ASSETS_DIR,
    RAW_INDEX,
    WIKI_INDEX,
    WIKI_SUMMARIES,
    init_vault_dirs,
)


@click.group()
@click.option(
    "--vault",
    type=click.Path(),
    default=None,
    help="Path to the vault directory.",
)
@click.pass_context
def main(ctx: click.Context, vault: str | None) -> None:
    """Wiki Compiler — LLM-powered knowledge management."""
    ctx.ensure_object(dict)
    from .vault.paths import resolve_vault

    vault_root = resolve_vault(vault)
    ctx.obj["vault_root"] = vault_root
    ctx.obj["config"] = load_config(vault_root)


@main.command()
@click.option("--dir", "directory", type=click.Path(), default="vault", help="Vault directory path.")
@click.pass_context
def init(ctx: click.Context, directory: str) -> None:
    """Initialize a new wiki vault."""
    vault_root = Path(directory).resolve()

    if (vault_root / ".wiki.toml").exists():
        error(f"Vault already initialized at {vault_root}")
        return

    info(f"Initializing vault at {vault_root}")

    # Create directory structure
    init_vault_dirs(vault_root)

    # Write default config
    write_default_config(vault_root)

    # Initialize Obsidian config
    init_obsidian_config(vault_root)

    # Create raw index
    now = datetime.now(timezone.utc).isoformat()
    write_frontmatter(
        vault_root / RAW_INDEX,
        {
            "type": "raw_index",
            "updated_at": now,
            "document_count": 0,
            "documents": [],
        },
        "# Raw Documents Index\n\nNo documents ingested yet.\n",
    )

    # Create wiki master index
    write_frontmatter(
        vault_root / WIKI_INDEX,
        {"type": "index", "updated_at": now, "article_count": 0},
        "# Wiki Index\n\nNo articles compiled yet.\n",
    )

    # Create wiki summaries
    write_frontmatter(
        vault_root / WIKI_SUMMARIES,
        {"type": "summaries", "updated_at": now},
        "# Article Summaries\n\n| Article | Category | Summary |\n|---------|----------|---------|\n",
    )

    # Create category index files
    for cat in WIKI_CATEGORIES:
        write_frontmatter(
            vault_root / WIKI_DIR / cat / "_index.md",
            {"type": "index", "category": cat, "updated_at": now, "article_count": 0},
            f"# {cat.title()} Index\n\nNo articles yet.\n",
        )

    success(f"Vault initialized at {vault_root}")
    info("Open this directory in Obsidian to browse the wiki.")


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show vault health overview."""
    vault_root: Path = ctx.obj["vault_root"]

    if not vault_root.exists():
        error(f"Vault not found at {vault_root}")
        info("Run 'wiki init' to create a new vault.")
        return

    # Count raw documents
    raw_dir = vault_root / RAW_DIR
    raw_count = sum(1 for f in raw_dir.rglob("*.md") if f.name != "_index.md") if raw_dir.exists() else 0

    # Count wiki articles
    wiki_dir = vault_root / WIKI_DIR
    wiki_count = sum(
        1 for f in wiki_dir.rglob("*.md")
        if f.name != "_index.md" and f.name != "_summaries.md"
    ) if wiki_dir.exists() else 0

    # Count output files
    output_dir = vault_root / OUTPUT_DIR
    output_count = sum(1 for f in output_dir.rglob("*") if f.is_file()) if output_dir.exists() else 0

    # Count assets
    assets_dir = vault_root / ASSETS_DIR
    asset_count = sum(1 for f in assets_dir.rglob("*") if f.is_file()) if assets_dir.exists() else 0

    # Count words in wiki
    word_count = 0
    if wiki_dir.exists():
        for f in wiki_dir.rglob("*.md"):
            try:
                word_count += len(f.read_text(encoding="utf-8").split())
            except (UnicodeDecodeError, PermissionError):
                pass

    # Category breakdown
    cat_counts = {}
    for cat in WIKI_CATEGORIES:
        cat_dir = wiki_dir / cat
        if cat_dir.exists():
            cat_counts[cat] = sum(
                1 for f in cat_dir.rglob("*.md") if f.name != "_index.md"
            )
        else:
            cat_counts[cat] = 0

    table = Table(title=f"Wiki Vault: {vault_root}")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Raw documents", str(raw_count))
    table.add_row("Wiki articles", str(wiki_count))
    table.add_row("Wiki words", f"{word_count:,}")
    table.add_row("Output files", str(output_count))
    table.add_row("Assets", str(asset_count))
    table.add_section()
    for cat, count in cat_counts.items():
        table.add_row(f"  {cat}", str(count))

    console.print(table)


# Register subcommand groups (imported lazily to avoid circular imports)
def _register_subcommands() -> None:
    from .ingest.cli import ingest
    from .compile.cli import compile
    from .qa.cli import ask
    from .lint.cli import lint
    from .search.cli import search

    main.add_command(ingest)
    main.add_command(compile)
    main.add_command(ask)
    main.add_command(lint)
    main.add_command(search)


_register_subcommands()
