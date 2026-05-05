from __future__ import annotations

import re
from pathlib import Path

from sitectl.models import CrawlResult, Finding, Page

SECRET_PATTERNS = {
    "secret.aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "secret.private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "secret.generic_token": re.compile(
        r"(?i)\b(api[_-]?key|token|secret)\b\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,})"
    ),
}


def scan_pages(pages: list[Page]) -> list[Finding]:
    findings: list[Finding] = []
    for page in pages:
        haystacks = [
            ("body", page.body),
            *[(f"header:{key}", value) for key, value in page.headers.items()],
        ]
        for _label, text in haystacks:
            for code, pattern in SECRET_PATTERNS.items():
                match = pattern.search(text)
                if match:
                    findings.append(
                        Finding(
                            "error",
                            code,
                            "Likely sensitive value exposed; evidence has been redacted.",
                            page.url,
                            redact(match.group(0)),
                        )
                    )
                    break
    return findings


def scan_assets(result: CrawlResult) -> list[Finding]:
    root = Path(result.target)
    if not root.exists() or not root.is_dir():
        return []
    findings: list[Finding] = []
    for rel in result.assets:
        path = root / rel
        if path.suffix.lower() not in {".js", ".map", ".json", ".txt", ".xml"}:
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for code, pattern in SECRET_PATTERNS.items():
            match = pattern.search(text)
            if match:
                findings.append(
                    Finding(
                        "error",
                        code,
                        "Likely sensitive value exposed in a static asset; "
                        "evidence has been redacted.",
                        str(path),
                        redact(match.group(0)),
                    )
                )
                break
    return findings


def redact(value: str) -> str:
    if len(value) <= 8:
        return "[REDACTED]"
    return f"{value[:4]}...[REDACTED]...{value[-4:]}"
