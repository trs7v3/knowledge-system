"""CLI commands for wiki search."""

from __future__ import annotations

from pathlib import Path

import click

from ..util.logging import info, success, console


@click.group()
def search():
    """Search the wiki."""
    pass


@search.command("query")
@click.argument("query_text")
@click.option("--limit", "-n", default=10, help="Max results to show.")
@click.pass_context
def search_query(ctx: click.Context, query_text: str, limit: int) -> None:
    """Full-text search over wiki articles."""
    from .engine import search as do_search
    from rich.table import Table

    vault_root: Path = ctx.obj["vault_root"]
    results = do_search(vault_root, query_text, limit=limit)

    if not results:
        info(f"No results for '{query_text}'")
        return

    table = Table(title=f"Search: {query_text}")
    table.add_column("Score", justify="right", width=6)
    table.add_column("Title")
    table.add_column("Category")
    table.add_column("Summary")

    for r in results:
        table.add_row(
            f"{r.score:.1f}",
            r.title,
            r.category,
            r.summary[:80] if r.summary else "",
        )

    console.print(table)


@search.command("serve")
@click.option("--port", "-p", default=8080, help="Port to serve on.")
@click.pass_context
def search_serve(ctx: click.Context, port: int) -> None:
    """Start the search web UI."""
    from .web_ui import create_app

    vault_root: Path = ctx.obj["vault_root"]
    config = ctx.obj["config"]
    port = config.search.web_ui_port or port

    app = create_app(vault_root)
    info(f"Starting search UI at http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)


@search.command("reindex")
@click.option("--include-raw", is_flag=True, help="Also index raw documents.")
@click.pass_context
def search_reindex(ctx: click.Context, include_raw: bool) -> None:
    """Rebuild the search index."""
    from .indexer import build_index

    vault_root: Path = ctx.obj["vault_root"]
    build_index(vault_root, include_raw=include_raw)
