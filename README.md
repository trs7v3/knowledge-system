# Wiki Compiler

An LLM-powered knowledge management system that ingests raw documents, compiles them into an Obsidian-compatible wiki, and provides Q&A, search, and linting capabilities. The LLM maintains the wiki — you rarely edit it directly.

## How It Works

```
Raw Sources ──> Ingest ──> raw/ ──> LLM Compile ──> wiki/ ──> Q&A / Search / Lint
(articles,       (CLI)     (markdown    (agentic      (Obsidian-     (CLI + 
 papers,                    + metadata)  tool-use       compatible     web UI)
 repos,                                  loop)          .md files)
 images)
```

1. **Ingest** source documents (web articles, PDFs, repos, images) into `raw/`
2. **Compile** them via LLM into categorized wiki articles with wikilinks and frontmatter
3. **Query** the wiki with natural language questions; get answers as markdown, slides, or charts
4. **Search** with full-text search (CLI and web UI)
5. **Lint** for broken links, inconsistencies, missing data, and new article suggestions
6. **Browse** everything in [Obsidian](https://obsidian.md) with full graph view support

The wiki scales to ~100+ articles / ~400K+ words without needing RAG — the LLM navigates via auto-maintained index and summary files.

## Setup

### Prerequisites

- Python 3.10+
- An Anthropic API key (for the `api` backend), **or** [Claude Code](https://claude.ai/code) installed (for the `claude-code` backend)
- [Obsidian](https://obsidian.md) (optional, for browsing the wiki)

### Install

```bash
git clone <this-repo>
cd knowledge-system
pip install -e .
```

For development (includes pytest):

```bash
pip install -e ".[dev]"
```

### Configure your API key

If using the default `api` backend:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Initialize a vault

```bash
wiki init --dir vault
```

This creates the full vault structure:

```
vault/
├── .obsidian/          # Obsidian config (auto-generated)
├── .wiki.toml          # Project configuration
├── raw/                # Ingested raw documents
│   ├── _index.md       # Raw document manifest
│   ├── articles/
│   ├── papers/
│   ├── repos/
│   └── images/
├── wiki/               # LLM-compiled wiki articles
│   ├── _index.md       # Master index
│   ├── _summaries.md   # One-line summaries (LLM navigation aid)
│   ├── concepts/       # Abstract ideas, theories, algorithms
│   ├── entities/       # People, organizations, tools
│   ├── techniques/     # How-to, methods, procedures
│   └── references/     # Factual data, tables, datasets
├── output/             # Q&A outputs, slides, charts
└── assets/             # Downloaded images
```

Open `vault/` in Obsidian to browse everything with graph view, backlinks, and wikilinks.

## Usage

### Ingest documents

```bash
# Web article (auto-downloads images)
wiki ingest url https://example.com/interesting-article

# Local markdown or text file
wiki ingest file path/to/document.md

# PDF
wiki ingest file path/to/paper.pdf

# Git repository (clones, extracts README + structure)
wiki ingest repo https://github.com/user/repo

# All supported files in a directory
wiki ingest dir path/to/folder/

# List ingested documents and their status
wiki ingest list
```

### Compile wiki

The compiler reads unprocessed raw documents, uses the LLM to generate wiki articles, and updates all index files.

```bash
# Compile new/changed documents (incremental)
wiki compile run

# Preview what would be compiled
wiki compile run --dry-run

# Recompile everything from scratch
wiki compile run --full

# Compile a specific document only
wiki compile run --doc raw/articles/my-article.md

# Regenerate index files without recompiling
wiki compile reindex

# LLM cross-article consistency pass (merge duplicates, fix links)
wiki compile reconcile
```

### Ask questions

The LLM reads the wiki's index/summary files to find relevant articles, reads them in full, then synthesizes an answer.

```bash
# Print answer to terminal
wiki ask "What are the key differences between transformers and RNNs?"

# Save as markdown file in output/
wiki ask "Summarize the main findings" --output md

# Generate a Marp slideshow
wiki ask "Create a presentation on gradient descent" --output marp

# Generate a matplotlib chart
wiki ask "Chart the timeline of major AI milestones" --output image

# Save output AND file it into the wiki for future queries
wiki ask "Compare X and Y" --output md --file
```

### Search

```bash
# Full-text search from the terminal
wiki search query "neural networks"

# Start the web search UI (default: localhost:8080)
wiki search serve

# Rebuild the search index
wiki search reindex
```

### Lint and health checks

```bash
# Run all structural checks (broken links, orphans, missing frontmatter)
wiki lint all

# LLM-driven deep consistency analysis
wiki lint consistency

# Find gaps and missing data
wiki lint completeness

# Suggest new articles based on existing content
wiki lint suggest

# Auto-fix issues using LLM
wiki lint fix
```

### Vault status

```bash
wiki status
```

```
       Wiki Vault: vault
┏━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric        ┃ Value ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Raw documents │    42 │
│ Wiki articles │    98 │
│ Wiki words    │ 387,201│
│ Output files  │    12 │
│ Assets        │   156 │
├───────────────┼───────┤
│   concepts    │    45 │
│   entities    │    23 │
│   techniques  │    18 │
│   references  │    12 │
└───────────────┴───────┘
```

## Configuration

Edit `vault/.wiki.toml` to customize behavior:

```toml
[llm]
model = "claude-sonnet-4-20250514"          # Default model
compilation_model = "claude-sonnet-4-20250514"  # Model for bulk compilation
qa_model = "claude-sonnet-4-20250514"           # Model for Q&A (can use a stronger model)
max_tokens_per_call = 8192
backend = "api"                          # "api" (Anthropic SDK) or "claude-code"

[ingest]
clipper_dir = "raw/inbox"
download_images = true

[search]
web_ui_port = 8080

[compile]
categories = ["concepts", "entities", "techniques", "references"]
```

### LLM Backend Options

**`api` (default)** — Direct Anthropic SDK calls with tool-use. The LLM gets tools (`read_file`, `write_file`, `list_dir`, `search_files`) and autonomously navigates the vault in an agentic loop. Requires `ANTHROPIC_API_KEY`.

**`claude-code`** — Delegates to the `claude` CLI. Claude Code handles its own file operations natively. Useful if you prefer Claude Code's built-in capabilities or want to avoid direct API costs.

## Architecture

### No-RAG Design

Instead of vector embeddings, the system maintains machine-readable index files:

- `wiki/_index.md` — master index with one-line descriptions (~5K tokens at 100 articles)
- `wiki/_summaries.md` — 2-3 sentence summaries (~15K tokens)
- `wiki/<category>/_index.md` — per-category indices

The LLM reads the summaries first to orient itself, then reads specific articles as needed. This is simple, debuggable, and works well up to hundreds of articles.

### Incremental Compilation

Each raw document gets a SHA-256 content hash. The compiler only processes new or changed documents. A full recompile is available via `--full` but rarely needed.

### Wiki Article Format

Every article uses YAML frontmatter compatible with Obsidian:

```yaml
---
title: "Gradient Descent"
category: concepts
sources: ["[[raw/articles/optimization-paper]]"]
created_at: 2026-04-03T12:00:00Z
updated_at: 2026-04-03T12:00:00Z
tags: [optimization, machine-learning]
summary: "Iterative first-order optimization algorithm for training models."
---

# Gradient Descent

Content with [[wikilinks]] to other articles...
```

## Typical Workflow

```bash
# 1. Initialize
wiki init --dir vault

# 2. Ingest some sources
wiki ingest url https://arxiv.org/abs/1706.03762  # Attention paper
wiki ingest url https://lilianweng.github.io/posts/2023-06-23-agent/
wiki ingest file ~/papers/rlhf-survey.pdf

# 3. Compile into wiki
wiki compile run

# 4. Browse in Obsidian — open vault/ as a vault

# 5. Ask questions
wiki ask "How does self-attention differ from cross-attention?"
wiki ask "Create slides on the evolution of LLM architectures" --output marp

# 6. Health check
wiki lint all
wiki lint suggest

# 7. Iterate — ingest more, recompile, query, repeat
wiki ingest url https://another-great-article.com
wiki compile run
```

## Project Structure

```
src/wikicompiler/
├── cli.py                  # Top-level Click CLI (wiki init, status)
├── ingest/                 # Document ingestion (web, PDF, repo, image)
├── compile/                # LLM compilation (compiler, indexer, linker)
├── qa/                     # Q&A system (navigator, answerer, renderer)
├── lint/                   # Health checks (consistency, completeness, suggestions)
├── search/                 # Full-text search (Whoosh index, Flask web UI)
├── llm/                    # Pluggable LLM backends (API, Claude Code)
├── vault/                  # Vault utilities (paths, frontmatter, wikilinks)
└── util/                   # Config, hashing, logging
```

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## License

MIT
