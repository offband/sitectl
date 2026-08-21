from __future__ import annotations

import fnmatch
import mimetypes
from collections import deque
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from sitectl.config import SiteConfig
from sitectl.html import parse_page
from sitectl.models import CrawlResult, NetworkSummary, Page

HTML_EXTENSIONS = {".html", ".htm"}


def crawl(target: str, config: SiteConfig, base_url: str | None = None) -> CrawlResult:
    parsed = urlparse(target)
    if parsed.scheme in {"http", "https"}:
        return crawl_http(target, config)
    return crawl_directory(
        Path(target), config, base_url or config.base_url or "https://example.local"
    )


def crawl_directory(root: Path, config: SiteConfig, base_url: str) -> CrawlResult:
    root = root.resolve()
    pages: list[Page] = []
    assets: list[str] = []
    errors: list[str] = []
    if not root.exists() or not root.is_dir():
        return CrawlResult(str(root), base_url, [], errors=[f"Directory does not exist: {root}"])

    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_dir() or _excluded(str(rel), config.excludes):
            continue
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix.lower() not in HTML_EXTENSIONS:
            assets.append(str(rel))
            continue
        try:
            body = path.read_text(errors="replace")
        except OSError as exc:
            errors.append(f"{rel}: {exc}")
            continue
        url = _file_url(base_url, rel, config.section_origins or {}, config.trailing_slash_urls)
        parser = parse_page(url, body)
        pages.append(
            Page(
                url=url,
                source_path=str(path),
                status_code=None,
                content_type=content_type,
                body=body,
                links=parser.links,
                anchors=parser.anchors,
                title=parser.title,
                description=parser.description,
                canonical=urljoin(url, parser.canonical) if parser.canonical else None,
            )
        )
    return CrawlResult(str(root), base_url.rstrip("/"), pages, assets=assets, errors=errors)


def crawl_http(start_url: str, config: SiteConfig) -> CrawlResult:
    start_url = _normalize_url(start_url)
    origin = _origin(start_url)
    pages: list[Page] = []
    errors: list[str] = []
    network = NetworkSummary(targets=[origin])
    seen: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])

    while queue:
        url, depth = queue.popleft()
        if url in seen or depth > config.max_depth or _excluded(url, config.excludes):
            continue
        seen.add(url)
        try:
            status, headers, body = _fetch(url, config, network)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            errors.append(f"{url}: {exc}")
            continue
        content_type = headers.get("content-type", "")
        if "html" not in content_type:
            continue
        parser = parse_page(url, body)
        page = Page(
            url=url,
            source_path=None,
            status_code=status,
            content_type=content_type,
            body=body,
            links=parser.links,
            anchors=parser.anchors,
            title=parser.title,
            description=parser.description,
            canonical=urljoin(url, parser.canonical) if parser.canonical else None,
            headers=headers,
        )
        pages.append(page)
        for link in page.links:
            absolute = _normalize_url(urljoin(url, link.target))
            if _excluded(absolute, config.excludes) or _excluded(
                urlparse(absolute).path, config.excludes
            ):
                continue
            if _origin(absolute) != origin:
                network.blocked_external += 1
                continue
            if absolute not in seen:
                queue.append((absolute, depth + 1))
    return CrawlResult(start_url, origin, pages, errors=errors, network=network)


def fetch_text(url: str, config: SiteConfig, network: NetworkSummary | None = None) -> str:
    _, _, body = _fetch(url, config, network or NetworkSummary())
    return body


def _fetch(
    url: str, config: SiteConfig, network: NetworkSummary
) -> tuple[int, dict[str, str], str]:
    network.requests += 1
    if url not in network.targets:
        network.targets.append(url)
    request = Request(url, headers={"User-Agent": config.user_agent})
    with urlopen(request, timeout=config.timeout) as response:  # noqa: S310
        raw = response.read()
        encoding = response.headers.get_content_charset() or "utf-8"
        headers = {key.lower(): value for key, value in response.headers.items()}
        return response.status, headers, raw.decode(encoding, errors="replace")


def _file_url(
    base_url: str,
    rel: Path,
    section_origins: dict[str, str] | None = None,
    trailing_slash: bool = False,
) -> str:
    parts = list(rel.parts)
    if parts[-1] in {"index.html", "index.htm"}:
        parts = parts[:-1]
    elif parts[-1].endswith((".html", ".htm")):
        parts[-1] = Path(parts[-1]).stem
    if parts and section_origins and parts[0] in section_origins:
        base_url = section_origins[parts[0]]
        parts = parts[1:]
    path = "/".join(parts)
    if not path:
        return f"{base_url.rstrip('/')}/" if trailing_slash else base_url.rstrip("/")
    url = f"{base_url.rstrip('/')}/{path}"
    return f"{url}/" if trailing_slash else url


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, path, "", parsed.query, ""))


def _origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _excluded(value: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(value, pattern) for pattern in patterns)
