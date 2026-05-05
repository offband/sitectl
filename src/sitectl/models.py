from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class Link:
    source: str
    target: str
    text: str = ""
    fragment: str = ""
    external: bool = False


@dataclass
class Page:
    url: str
    source_path: str | None
    status_code: int | None
    content_type: str
    body: str
    links: list[Link] = field(default_factory=list)
    anchors: set[str] = field(default_factory=set)
    title: str | None = None
    description: str | None = None
    canonical: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class NetworkSummary:
    requests: int = 0
    external_requests: int = 0
    blocked_external: int = 0
    targets: list[str] = field(default_factory=list)


@dataclass
class CrawlResult:
    target: str
    base_url: str
    pages: list[Page]
    assets: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    network: NetworkSummary = field(default_factory=NetworkSummary)


@dataclass(frozen=True)
class Finding:
    severity: Severity
    code: str
    message: str
    location: str | None = None
    evidence: str | None = None


@dataclass
class AuditReport:
    target: str
    base_url: str
    findings: list[Finding]
    pages_scanned: int
    network: NetworkSummary

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["findings"] = [asdict(finding) for finding in self.findings]
        return data
