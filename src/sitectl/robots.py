from __future__ import annotations

from pathlib import Path

from sitectl.models import Finding

KNOWN_FIELDS = {"user-agent", "allow", "disallow", "sitemap", "crawl-delay"}


def validate_robots_text(text: str, location: str = "robots.txt") -> list[Finding]:
    findings: list[Finding] = []
    saw_user_agent = False
    for number, line in enumerate(text.splitlines(), start=1):
        clean = line.split("#", 1)[0].strip()
        if not clean:
            continue
        if ":" not in clean:
            findings.append(
                Finding(
                    "error",
                    "robots.syntax",
                    "Robots directive must contain ':'.",
                    f"{location}:{number}",
                    clean,
                )
            )
            continue
        field, value = clean.split(":", 1)
        field = field.strip().lower()
        value = value.strip()
        if field not in KNOWN_FIELDS:
            findings.append(
                Finding(
                    "warning",
                    "robots.unknown_field",
                    f"Unknown robots directive '{field}'.",
                    f"{location}:{number}",
                )
            )
        if field == "user-agent":
            saw_user_agent = True
            if not value:
                findings.append(
                    Finding(
                        "error", "robots.empty_user_agent", "User-agent cannot be empty.", location
                    )
                )
        if field == "sitemap" and not value.startswith(("http://", "https://")):
            findings.append(
                Finding(
                    "error",
                    "robots.relative_sitemap",
                    "Sitemap directive must be an absolute URL.",
                    location,
                )
            )
    if text.strip() and not saw_user_agent:
        findings.append(
            Finding(
                "warning",
                "robots.no_user_agent",
                "Robots file has no user-agent directive.",
                location,
            )
        )
    return findings


def read_robots(path: str) -> str:
    return Path(path).read_text()
