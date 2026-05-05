from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from sitectl.models import AuditReport, CrawlResult, Finding

console = Console()


def write_json(data: dict[str, Any], output: str | None) -> None:
    text = json.dumps(data, indent=2, sort_keys=True)
    if output:
        Path(output).write_text(text + "\n")
    else:
        console.print(text)


def crawl_to_dict(result: CrawlResult) -> dict[str, Any]:
    return {
        "target": result.target,
        "base_url": result.base_url,
        "pages": [
            {
                "url": page.url,
                "source_path": page.source_path,
                "status_code": page.status_code,
                "title": page.title,
                "description": page.description,
                "canonical": page.canonical,
                "links": [asdict(link) for link in page.links],
            }
            for page in result.pages
        ],
        "assets": result.assets,
        "errors": result.errors,
        "network": asdict(result.network),
    }


def print_crawl(result: CrawlResult) -> None:
    console.print(f"[bold]Crawled[/bold] {result.target}")
    console.print(
        f"Pages: {len(result.pages)}  Assets: {len(result.assets)}  Errors: {len(result.errors)}"
    )
    if result.network.requests:
        print_network(result.network)


def print_findings(findings: list[Finding]) -> None:
    if not findings:
        console.print("[green]No findings.[/green]")
        return
    table = Table("Severity", "Code", "Location", "Message", "Evidence")
    for finding in findings:
        table.add_row(
            finding.severity,
            finding.code,
            finding.location or "",
            finding.message,
            finding.evidence or "",
        )
    console.print(table)


def print_audit(report: AuditReport) -> None:
    counts = Counter(finding.severity for finding in report.findings)
    console.print(f"[bold]Audit[/bold] {report.target}")
    console.print(
        f"Pages: {report.pages_scanned}  Errors: {counts['error']}  "
        f"Warnings: {counts['warning']}  Info: {counts['info']}"
    )
    print_findings(report.findings)
    if report.network.requests:
        print_network(report.network)


def print_network(network) -> None:
    console.print(
        "[dim]Network: "
        f"requests={network.requests}, external_requests={network.external_requests}, "
        f"blocked_external={network.blocked_external}[/dim]"
    )


def exit_code(findings: list[Finding]) -> int:
    return 1 if any(finding.severity == "error" for finding in findings) else 0
