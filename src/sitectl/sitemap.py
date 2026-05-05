from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

from sitectl.models import CrawlResult, Finding

NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", NS)


def generate_sitemap(result: CrawlResult) -> str:
    root = ET.Element(f"{{{NS}}}urlset")
    for page in sorted(result.pages, key=lambda item: item.url):
        item = ET.SubElement(root, f"{{{NS}}}url")
        loc = ET.SubElement(item, f"{{{NS}}}loc")
        loc.text = page.url
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def validate_sitemap_text(text: str, location: str = "sitemap") -> list[Finding]:
    findings: list[Finding] = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return [
            Finding(
                "error", "sitemap.invalid_xml", "Sitemap XML is not parseable.", location, str(exc)
            )
        ]
    if _strip_ns(root.tag) != "urlset":
        findings.append(
            Finding("error", "sitemap.unsupported_root", "Sitemap root must be urlset.", location)
        )
        return findings
    locs = root.findall(f".//{{{NS}}}loc") or root.findall(".//loc")
    if not locs:
        findings.append(
            Finding("warning", "sitemap.empty", "Sitemap contains no URL entries.", location)
        )
    for loc in locs:
        value = (loc.text or "").strip()
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            findings.append(
                Finding(
                    "error",
                    "sitemap.invalid_url",
                    "Sitemap URL must be absolute HTTP(S).",
                    location,
                    value,
                )
            )
    return findings


def extract_sitemap_urls(text: str) -> set[str]:
    root = ET.fromstring(text)
    locs = root.findall(f".//{{{NS}}}loc") or root.findall(".//loc")
    return {(loc.text or "").strip() for loc in locs if (loc.text or "").strip()}


def read_sitemap(path: str) -> str:
    return Path(path).read_text()


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
