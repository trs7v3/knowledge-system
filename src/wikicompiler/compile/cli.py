"""CLI commands for wiki compilation."""

from __future__ import annotations

from pathlib import Path

import click

from ..util.logging import info, success


@click.group()
def compile():
    """Compile raw documents into wiki articles."""
    pass


@compile.command("run")
@click.option("--full", is_flag=True, help="Recompile all documents from scratch.")
@click.option("--dry-run", is_flag=True, help="Show what would be compiled without doing it.")
@click.option("--doc", "specific_doc", default=None, help="Compile a specific raw document only.")
@click.pass_context
def compile_run(
    ctx: click.Context, full: bool, dry_run: bool, specific_doc: str | None
) -> None:
    """Compile new/changed raw documents into wiki articles."""
    from .compiler import compile_wiki

    vault_root: Path = ctx.obj["vault_root"]
    config = ctx.obj["config"]

    produced = compile_wiki(
        vault_root=vault_root,
        config=config,
        full=full,
        dry_run=dry_run,
        specific_doc=specific_doc,
    )


@compile.command("reindex")
@click.pass_context
def compile_reindex(ctx: click.Context) -> None:
    """Regenerate all index files and summaries."""
    from .indexer import rebuild_indices

    vault_root: Path = ctx.obj["vault_root"]
    rebuild_indices(vault_root)


@compile.command("reconcile")
@click.pass_context
def compile_reconcile(ctx: click.Context) -> None:
    """Run cross-article consistency pass using LLM."""
    from ..llm import create_backend
    from ..llm.prompts import RECONCILE_SYSTEM
    from ..llm.tools import VAULT_TOOLS, ToolHandler
    from ..util.logging import status

    vault_root: Path = ctx.obj["vault_root"]
    config = ctx.obj["config"]
    backend = create_backend(config)

    with status("Running reconciliation pass..."):
        responses = backend.agentic_loop(
            system_prompt=RECONCILE_SYSTEM,
            initial_message="Please review the wiki for consistency issues, broken links, and duplicates. Read wiki/_summaries.md first.",
            tools=VAULT_TOOLS,
            tool_handler=ToolHandler(vault_root),
            max_turns=20,
        )

    # Print the final response
    if responses:
        info(responses[-1].content)

    # Rebuild indices after reconciliation
    from .indexer import rebuild_indices
    rebuild_indices(vault_root)
    success("Reconciliation complete.")


@compile.command("status")
@click.pass_context
def compile_status(ctx: click.Context) -> None:
    """Show compilation status."""
    from ..ingest.metadata import get_unprocessed_docs
    from rich.table import Table
    from ..util.logging import console

    vault_root: Path = ctx.obj["vault_root"]
    unprocessed = get_unprocessed_docs(vault_root)

    if unprocessed:
        table = Table(title="Pending Compilation")
        table.add_column("Title")
        table.add_column("Type")
        table.add_column("Path")

        for doc in unprocessed:
            table.add_row(
                doc.get("title", "?"),
                doc.get("source_type", "?"),
                doc.get("path", "?"),
            )
        console.print(table)
    else:
        success("All documents are compiled.")
