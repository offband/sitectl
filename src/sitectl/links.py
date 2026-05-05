from __future__ import annotations

from urllib.parse import urldefrag, urljoin, urlparse

from sitectl.config import DEFAULT_EXCLUDES
from sitectl.models import CrawlResult, Finding


def check_links(result: CrawlResult) -> list[Finding]:
    findings: list[Finding] = []
    page_by_url = {_normalize(page.url): page for page in result.pages}
    for page in result.pages:
        for link in page.links:
            absolute = urljoin(page.url, link.target)
            clean, fragment = urldefrag(absolute)
            fragment = fragment or link.fragment
            if _ignored_scheme(clean):
                continue
            clean = _normalize(clean)
            if _excluded(clean) or _excluded(urlparse(clean).path):
                continue
            if _external(result.base_url, clean):
                continue
            target_page = page_by_url.get(clean)
            if target_page is None:
                findings.append(
                    Finding(
                        "error",
                        "link.broken_internal",
                        "Internal link target was not found.",
                        page.url,
                        absolute,
                    )
                )
                continue
            if fragment and fragment not in target_page.anchors:
                findings.append(
                    Finding(
                        "error",
                        "link.broken_anchor",
                        "Internal link anchor was not found.",
                        page.url,
                        absolute,
                    )
                )
    return findings


def _external(base_url: str, url: str) -> bool:
    base = urlparse(base_url)
    parsed = urlparse(url)
    return bool(parsed.netloc and parsed.netloc != base.netloc)


def _ignored_scheme(url: str) -> bool:
    return urlparse(url).scheme in {"mailto", "tel", "javascript", "data"}


def _normalize(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path == "/":
        return parsed._replace(path="", fragment="").geturl()
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return parsed._replace(path=path, fragment="").geturl()


def _excluded(value: str) -> bool:
    from fnmatch import fnmatch

    return any(fnmatch(value, pattern) for pattern in DEFAULT_EXCLUDES)
