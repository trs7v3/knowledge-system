"""CLI commands for wiki linting and health checks."""

from __future__ import annotations

from pathlib import Path

import click

from ..util.logging import info, success, warn, error, console


@click.group()
def lint():
    """Run wiki health checks and linting."""
    pass


@lint.command("all")
@click.pass_context
def lint_all(ctx: click.Context) -> None:
    """Run all structural lint checks."""
    from .consistency import run_all_checks
    from rich.table import Table

    vault_root: Path = ctx.obj["vault_root"]
    issues = run_all_checks(vault_root)

    if not issues:
        success("No issues found!")
        return

    table = Table(title=f"Lint Results ({len(issues)} issues)")
    table.add_column("Severity", style="bold")
    table.add_column("Category")
    table.add_column("File")
    table.add_column("Message")

    for issue in issues:
        sev_style = {"error": "red", "warning": "yellow", "info": "blue"}.get(
            issue.severity, "white"
        )
        table.add_row(
            f"[{sev_style}]{issue.severity}[/{sev_style}]",
            issue.category,
            issue.file,
            issue.message,
        )

    console.print(table)


@lint.command("consistency")
@click.pass_context
def lint_consistency(ctx: click.Context) -> None:
    """Check cross-article consistency using LLM."""
    from ..llm import create_backend
    from ..llm.prompts import LINT_CONSISTENCY_SYSTEM
    from ..llm.tools import VAULT_TOOLS, ToolHandler
    from ..util.logging import status

    vault_root: Path = ctx.obj["vault_root"]
    config = ctx.obj["config"]
    backend = create_backend(config)

    with status("Checking consistency..."):
        responses = backend.agentic_loop(
            system_prompt=LINT_CONSISTENCY_SYSTEM,
            initial_message="Analyze the wiki for inconsistencies. Read wiki/_summaries.md first.",
            tools=VAULT_TOOLS,
            tool_handler=ToolHandler(vault_root),
            max_turns=15,
        )

    if responses:
        console.print(responses[-1].content)


@lint.command("completeness")
@click.pass_context
def lint_completeness(ctx: click.Context) -> None:
    """Find missing data and gaps in the wiki."""
    from .completeness import check_completeness

    vault_root: Path = ctx.obj["vault_root"]
    config = ctx.obj["config"]
    result = check_completeness(vault_root, config)
    console.print(result)


@lint.command("suggest")
@click.pass_context
def lint_suggest(ctx: click.Context) -> None:
    """Suggest new articles based on existing content."""
    from .suggestions import suggest_articles

    vault_root: Path = ctx.obj["vault_root"]
    config = ctx.obj["config"]
    result = suggest_articles(vault_root, config)
    console.print(result)


@lint.command("fix")
@click.pass_context
def lint_fix(ctx: click.Context) -> None:
    """Auto-fix issues using LLM (broken links, missing frontmatter)."""
    from .consistency import run_all_checks
    from ..llm import create_backend
    from ..llm.tools import VAULT_TOOLS, ToolHandler
    from ..util.logging import status

    vault_root: Path = ctx.obj["vault_root"]
    config = ctx.obj["config"]

    issues = run_all_checks(vault_root)
    if not issues:
        success("No issues to fix!")
        return

    info(f"Found {len(issues)} issues. Attempting auto-fix...")

    issue_report = "\n".join(
        f"- [{i.severity}] {i.category} in {i.file}: {i.message}"
        for i in issues
    )

    backend = create_backend(config)
    with status("Fixing issues..."):
        responses = backend.agentic_loop(
            system_prompt=(
                "You are a wiki maintenance agent. Fix the following issues in the wiki. "
                "Read the affected files, make corrections, and write them back.\n\n"
                f"Issues to fix:\n{issue_report}"
            ),
            initial_message="Please fix these wiki issues. Start by reading the affected files.",
            tools=VAULT_TOOLS,
            tool_handler=ToolHandler(vault_root),
            max_turns=20,
        )

    if responses:
        console.print(responses[-1].content)

    # Re-check
    remaining = run_all_checks(vault_root)
    if remaining:
        warn(f"{len(remaining)} issues remain after auto-fix.")
    else:
        success("All issues fixed!")
