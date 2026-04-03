"""Global configuration loading from .wiki.toml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class LLMConfig:
    model: str = "claude-sonnet-4-20250514"
    compilation_model: str = "claude-sonnet-4-20250514"
    qa_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 8192
    backend: str = "api"  # "api" or "claude-code"


@dataclass
class IngestConfig:
    clipper_dir: str = "raw/inbox"
    download_images: bool = True


@dataclass
class SearchConfig:
    web_ui_port: int = 8080


@dataclass
class CompileConfig:
    categories: list[str] = field(
        default_factory=lambda: ["concepts", "entities", "techniques", "references"]
    )


@dataclass
class Config:
    vault_path: Path = field(default_factory=lambda: Path("vault"))
    llm: LLMConfig = field(default_factory=LLMConfig)
    ingest: IngestConfig = field(default_factory=IngestConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    compile: CompileConfig = field(default_factory=CompileConfig)


def load_config(vault_root: Path) -> Config:
    """Load configuration from .wiki.toml in the vault root."""
    config_path = vault_root / ".wiki.toml"
    if not config_path.exists():
        return Config(vault_path=vault_root)

    # We use TOML-like YAML for simplicity (toml requires extra dep)
    # Actually read as YAML since we have pyyaml
    raw = _load_toml_as_dict(config_path)
    return _dict_to_config(raw, vault_root)


def _load_toml_as_dict(path: Path) -> dict[str, Any]:
    """Parse a simple TOML file. Supports basic key=value and [sections]."""
    result: dict[str, Any] = {}
    current_section: dict[str, Any] | None = None

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1].strip()
            result[section_name] = {}
            current_section = result[section_name]
        elif "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Strip inline comments (but not inside strings)
            if not value.startswith('"') and "#" in value:
                value = value[:value.index("#")].strip()
            elif value.startswith('"'):
                # Find closing quote, then strip comment after
                closing = value.index('"', 1) if '"' in value[1:] else -1
                if closing > 0 and "#" in value[closing:]:
                    value = value[:closing + 1].strip()
            # Parse value
            parsed = _parse_toml_value(value)
            target = current_section if current_section is not None else result
            target[key] = parsed

    return result


def _parse_toml_value(value: str) -> Any:
    """Parse a simple TOML value."""
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_toml_value(v.strip()) for v in inner.split(",")]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _dict_to_config(raw: dict[str, Any], vault_root: Path) -> Config:
    """Convert raw dict to Config dataclass."""
    config = Config(vault_path=vault_root)

    if "llm" in raw:
        llm = raw["llm"]
        config.llm = LLMConfig(
            model=llm.get("model", config.llm.model),
            compilation_model=llm.get("compilation_model", config.llm.compilation_model),
            qa_model=llm.get("qa_model", config.llm.qa_model),
            max_tokens=llm.get("max_tokens_per_call", config.llm.max_tokens),
            backend=llm.get("backend", config.llm.backend),
        )

    if "ingest" in raw:
        ing = raw["ingest"]
        config.ingest = IngestConfig(
            clipper_dir=ing.get("clipper_dir", config.ingest.clipper_dir),
            download_images=ing.get("download_images", config.ingest.download_images),
        )

    if "search" in raw:
        config.search = SearchConfig(
            web_ui_port=raw["search"].get("web_ui_port", config.search.web_ui_port)
        )

    if "compile" in raw:
        config.compile = CompileConfig(
            categories=raw["compile"].get("categories", config.compile.categories)
        )

    return config


def write_default_config(vault_root: Path) -> Path:
    """Write a default .wiki.toml configuration file."""
    config_path = vault_root / ".wiki.toml"
    config_path.write_text(
        """\
# Wiki Compiler Configuration

[llm]
model = "claude-sonnet-4-20250514"
compilation_model = "claude-sonnet-4-20250514"
qa_model = "claude-sonnet-4-20250514"
max_tokens_per_call = 8192
backend = "api"  # "api" or "claude-code"

[ingest]
clipper_dir = "raw/inbox"
download_images = true

[search]
web_ui_port = 8080

[compile]
categories = ["concepts", "entities", "techniques", "references"]
""",
        encoding="utf-8",
    )
    return config_path
