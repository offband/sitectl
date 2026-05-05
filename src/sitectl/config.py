from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_EXCLUDES = ("/cdn-cgi/*", "*/cdn-cgi/*")
GLOBAL_CONFIG = Path("~/.sitectl/config.toml")
LOCAL_CONFIG = Path("sitectl.toml")
DEFAULT_CONFIG_TEXT = """# Starter sitectl config.
#
# Personal defaults live at ~/.sitectl/config.toml.
# Project defaults can live at ./sitectl.toml.

max_depth = 3
timeout = 10
user_agent = "sitectl/0.1 local-first"
privacy = "strict"

# These are appended to sitectl's built-in safety excludes, which include /cdn-cgi/*.
excludes = [
  "admin/*",
  "*.draft.html",
]

# Usually better in a project sitectl.toml than in ~/.sitectl/config.toml.
# base_url = "https://example.com"
"""


@dataclass(frozen=True)
class SiteConfig:
    base_url: str | None = None
    excludes: tuple[str, ...] = DEFAULT_EXCLUDES
    max_depth: int = 3
    timeout: float = 10.0
    user_agent: str = "sitectl/0.1 local-first"
    output: str | None = None
    privacy: str = "strict"


def load_config(path: Path | None = None) -> SiteConfig:
    config = SiteConfig()
    for config_path in _config_paths(path):
        if config_path.exists():
            config = _merge_config(config, _read_raw_config(config_path))
    return config


def default_config_path() -> Path:
    return GLOBAL_CONFIG.expanduser()


def config_search_paths(path: Path | None = None) -> tuple[Path, ...]:
    return _config_paths(path)


def resolved_config_paths(path: Path | None = None) -> tuple[Path, ...]:
    return tuple(candidate for candidate in config_search_paths(path) if candidate.exists())


def dump_default_config() -> str:
    return DEFAULT_CONFIG_TEXT


def dump_resolved_config(config: SiteConfig) -> dict[str, Any]:
    data = asdict(config)
    data["excludes"] = list(config.excludes)
    return data


def _config_paths(path: Path | None) -> tuple[Path, ...]:
    project_path = path or LOCAL_CONFIG
    return (GLOBAL_CONFIG.expanduser(), project_path)


def _read_raw_config(path: Path) -> dict:
    data = tomllib.loads(path.read_text())
    return data.get("sitectl", data)


def _merge_config(config: SiteConfig, raw: dict) -> SiteConfig:
    excludes = config.excludes
    if "excludes" in raw:
        excludes = (*excludes, *tuple(raw["excludes"]))
    return SiteConfig(
        base_url=raw.get("base_url", config.base_url),
        excludes=tuple(dict.fromkeys(excludes)),
        max_depth=int(raw.get("max_depth", config.max_depth)),
        timeout=float(raw.get("timeout", config.timeout)),
        user_agent=raw.get("user_agent", config.user_agent),
        output=raw.get("output", config.output),
        privacy=raw.get("privacy", config.privacy),
    )
