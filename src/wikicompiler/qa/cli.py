"""CLI commands for Q&A."""

from __future__ import annotations

from pathlib import Path

import click

from ..util.logging import info, success, console


@click.command()
@click.argument("question")
@click.option("--output", "-o", type=click.Choice(["text", "md", "marp", "image"]), default="text", help="Output format.")
@click.option("--file", "file_to_wiki", is_flag=True, help="File the output into the wiki.")
@click.option("--title", "-t", default=None, help="Title for saved output files.")
@click.pass_context
def ask(ctx: click.Context, question: str, output: str, file_to_wiki: bool, title: str | None) -> None:
    """Ask a question against the wiki."""
    from .answerer import ask_question
    from .renderer import save_markdown, save_marp_slides, save_chart, file_to_wiki as do_file

    vault_root: Path = ctx.obj["vault_root"]
    config = ctx.obj["config"]

    # Map output format
    format_map = {"text": "text", "md": "text", "marp": "marp", "image": "chart"}
    fmt = format_map.get(output, "text")

    answer = ask_question(vault_root, config, question, output_format=fmt)

    if output == "text":
        # Print to stdout
        console.print(answer)
    elif output == "md":
        path = save_markdown(vault_root, answer, title=title)
        success(f"Saved to {path}")
    elif output == "marp":
        path = save_marp_slides(vault_root, answer, title=title)
        success(f"Saved slideshow to {path}")
    elif output == "image":
        path = save_chart(vault_root, answer, title=title)
        success(f"Saved chart to {path}")
    else:
        console.print(answer)

    # File into wiki if requested
    if file_to_wiki and output in ("md", "marp"):
        filed_path = do_file(vault_root, path)
        if filed_path:
            success(f"Filed into wiki at {filed_path}")
