from __future__ import annotations

from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin

from sitectl.config import SiteConfig
from sitectl.crawler import crawl, fetch_text
from sitectl.links import check_links
from sitectl.models import AuditReport, CrawlResult, Finding
from sitectl.robots import validate_robots_text
from sitectl.security import scan_assets, scan_pages
from sitectl.sitemap import extract_sitemap_urls, validate_sitemap_text


def run_audit(target: str, config: SiteConfig, base_url: str | None = None) -> AuditReport:
    result = crawl(target, config, base_url)
    findings: list[Finding] = []
    findings.extend(Finding("error", "crawl.error", error) for error in result.errors)
    findings.extend(_sitemap_findings(result, config))
    findings.extend(_robots_findings(result, config))
    findings.extend(check_links(result))
    findings.extend(_metadata_findings(result.pages))
    findings.extend(scan_pages(result.pages))
    findings.extend(scan_assets(result))
    if not result.pages:
        findings.append(
            Finding("error", "crawl.no_pages", "No HTML pages were discovered.", target)
        )
    return AuditReport(target, result.base_url, findings, len(result.pages), result.network)


def _sitemap_findings(result: CrawlResult, config: SiteConfig) -> list[Finding]:
    location = _local_file(result, "sitemap.xml")
    if location and location.exists():
        text = location.read_text(errors="replace")
        source = str(location)
    elif result.base_url.startswith(("http://", "https://")) and not Path(result.target).exists():
        source = urljoin(result.base_url + "/", "sitemap.xml")
        try:
            text = fetch_text(source, config, result.network)
        except (HTTPError, URLError, TimeoutError, OSError):
            return [Finding("warning", "sitemap.missing", "No sitemap.xml was found.", source)]
    else:
        return [Finding("warning", "sitemap.missing", "No sitemap.xml was found.", result.target)]

    findings = validate_sitemap_text(text, source)
    if any(finding.severity == "error" for finding in findings):
        return findings
    page_urls = {page.url for page in result.pages}
    sitemap_urls = extract_sitemap_urls(text)
    for url in sorted(page_urls - sitemap_urls):
        findings.append(
            Finding(
                "warning", "sitemap.page_missing", "Discovered page is missing from sitemap.", url
            )
        )
    for url in sorted(sitemap_urls - page_urls):
        findings.append(
            Finding(
                "warning", "sitemap.url_unseen", "Sitemap URL was not discovered by crawl.", url
            )
        )
    return findings


def _robots_findings(result: CrawlResult, config: SiteConfig) -> list[Finding]:
    location = _local_file(result, "robots.txt")
    if location and location.exists():
        return validate_robots_text(location.read_text(errors="replace"), str(location))
    if result.base_url.startswith(("http://", "https://")) and not Path(result.target).exists():
        source = urljoin(result.base_url + "/", "robots.txt")
        try:
            return validate_robots_text(fetch_text(source, config, result.network), source)
        except (HTTPError, URLError, TimeoutError, OSError):
            return [Finding("warning", "robots.missing", "No robots.txt was found.", source)]
    return [Finding("warning", "robots.missing", "No robots.txt was found.", result.target)]


def _local_file(result: CrawlResult, name: str) -> Path | None:
    root = Path(result.target)
    if root.exists() and root.is_dir():
        return root / name
    return None


def _metadata_findings(pages) -> list[Finding]:
    findings: list[Finding] = []
    titles = Counter(page.title for page in pages if page.title)
    for page in pages:
        if not page.title:
            findings.append(
                Finding("warning", "meta.missing_title", "Page is missing a title.", page.url)
            )
        elif titles[page.title] > 1:
            findings.append(
                Finding(
                    "warning",
                    "meta.duplicate_title",
                    "Page title is duplicated.",
                    page.url,
                    page.title,
                )
            )
        if not page.description:
            findings.append(
                Finding(
                    "warning",
                    "meta.missing_description",
                    "Page is missing a description.",
                    page.url,
                )
            )
        if page.canonical and page.canonical != page.url:
            findings.append(
                Finding(
                    "warning",
                    "meta.canonical_mismatch",
                    "Canonical URL does not match page URL.",
                    page.url,
                    page.canonical,
                )
            )
    return findings
