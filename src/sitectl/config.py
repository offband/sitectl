from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_EXCLUDES = ("/cdn-cgi/*", "*/cdn-cgi/*")
GLOBAL_CONFIG = Path("~/.sitectl")
LOCAL_CONFIG = Path("sitectl.toml")


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
