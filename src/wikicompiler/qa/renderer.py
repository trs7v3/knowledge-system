"""Output rendering: markdown files, Marp slides, matplotlib charts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..vault.frontmatter import write_frontmatter
from ..vault.paths import OUTPUT_DIR, slug


def save_markdown(
    vault_root: Path, content: str, title: str | None = None
) -> Path:
    """Save answer as a markdown file in the output directory."""
    if not title:
        title = f"answer-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    filename = f"{slug(title)}.md"
    rel_path = f"{OUTPUT_DIR}/{filename}"

    meta = {
        "title": title,
        "type": "output",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tags": ["output", "answer"],
    }
    write_frontmatter(vault_root / rel_path, meta, content)
    return vault_root / rel_path


def save_marp_slides(
    vault_root: Path, content: str, title: str | None = None
) -> Path:
    """Save answer as a Marp slideshow."""
    if not title:
        title = f"slides-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    filename = f"{slug(title)}.md"
    rel_path = f"{OUTPUT_DIR}/{filename}"

    # Ensure Marp header is present
    if not content.strip().startswith("---"):
        content = f"---\nmarp: true\ntheme: default\n---\n\n{content}"

    (vault_root / rel_path).parent.mkdir(parents=True, exist_ok=True)
    (vault_root / rel_path).write_text(content, encoding="utf-8")
    return vault_root / rel_path


def save_chart(
    vault_root: Path, chart_json: str, title: str | None = None
) -> Path:
    """Render chart JSON as a matplotlib image and save it."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        data = json.loads(chart_json)
    except json.JSONDecodeError:
        # If not valid JSON, save as text
        return save_markdown(vault_root, chart_json, title)

    if not title:
        title = data.get("title", f"chart-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}")

    chart_type = data.get("chart_type", "bar")
    labels = data.get("labels", [])
    datasets = data.get("datasets", [])

    fig, ax = plt.subplots(figsize=(10, 6))

    for dataset in datasets:
        ds_data = dataset.get("data", [])
        ds_label = dataset.get("label", "")

        if chart_type == "bar":
            ax.bar(labels, ds_data, label=ds_label, alpha=0.7)
        elif chart_type == "line":
            ax.plot(labels, ds_data, label=ds_label, marker="o")
        elif chart_type == "pie":
            ax.pie(ds_data, labels=labels, autopct="%1.1f%%")
        elif chart_type == "scatter":
            ax.scatter(range(len(ds_data)), ds_data, label=ds_label)

    ax.set_title(data.get("title", ""))
    if datasets and chart_type != "pie":
        ax.legend()

    plt.tight_layout()

    filename = f"{slug(title)}.png"
    rel_path = f"{OUTPUT_DIR}/{filename}"
    (vault_root / OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    fig.savefig(vault_root / rel_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return vault_root / rel_path


def file_to_wiki(vault_root: Path, output_path: Path) -> Path | None:
    """Move an output file into the wiki for future reference."""
    from ..vault.paths import WIKI_DIR

    if not output_path.exists():
        return None

    dest_dir = vault_root / WIKI_DIR / "references"
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / output_path.name
    output_path.rename(dest)

    # Update frontmatter to reflect new location
    if dest.suffix == ".md":
        from ..vault.frontmatter import update_frontmatter
        update_frontmatter(dest, {
            "category": "references",
            "filed_from": str(output_path.relative_to(vault_root)),
        })

    return dest
