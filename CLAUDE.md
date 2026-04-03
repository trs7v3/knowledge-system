# Wiki Compiler — Claude Code Instructions

This is an LLM-powered wiki compiler. The vault lives at `vault/` and is an Obsidian-compatible directory.

## Vault Structure
- `vault/raw/` — ingested raw documents (articles, papers, repos, images)
- `vault/wiki/` — compiled wiki articles organized by category
- `vault/output/` — Q&A outputs, slides, charts
- `vault/assets/` — downloaded images and attachments

## Key Files
- `vault/raw/_index.md` — manifest of all raw documents with processing status
- `vault/wiki/_index.md` — master wiki index
- `vault/wiki/_summaries.md` — one-line summaries of every wiki article
- `vault/wiki/<category>/_index.md` — per-category indices

## Conventions
- All wiki articles use YAML frontmatter with: title, category, sources, created_at, updated_at, tags, summary
- Wikilinks use `[[article-name]]` syntax (Obsidian-compatible)
- Article filenames are kebab-case
- Categories: concepts, entities, techniques, references

## CLI
Install: `pip install -e .`
Commands: `wiki init`, `wiki ingest`, `wiki compile`, `wiki ask`, `wiki lint`, `wiki search`, `wiki status`

## When Acting as LLM Backend
When used as the LLM layer for compilation or Q&A:
1. Read `vault/wiki/_summaries.md` first to understand what exists
2. Read `vault/raw/_index.md` to find unprocessed documents
3. For each unprocessed doc, read it, then create/update wiki articles
4. Always include proper YAML frontmatter and wikilinks
5. Update index files after making changes
