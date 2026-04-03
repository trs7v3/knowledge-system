"""Rich-based logging setup for the wiki compiler."""

from __future__ import annotations

from rich.console import Console

console = Console()


def info(msg: str) -> None:
    console.print(f"[blue]INFO[/blue]  {msg}")


def success(msg: str) -> None:
    console.print(f"[green]OK[/green]    {msg}")


def warn(msg: str) -> None:
    console.print(f"[yellow]WARN[/yellow]  {msg}")


def error(msg: str) -> None:
    console.print(f"[red]ERROR[/red] {msg}")


def status(msg: str):
    """Return a Rich status context manager for spinner display."""
    return console.status(msg)
