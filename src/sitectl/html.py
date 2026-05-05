from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urldefrag

from sitectl.models import Link


class PageParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.links: list[Link] = []
        self.anchors: set[str] = set()
        self.title: str | None = None
        self.description: str | None = None
        self.canonical: str | None = None
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): value or "" for key, value in attrs}
        if tag == "a":
            href = attr.get("href")
            if href:
                clean, fragment = urldefrag(href)
                self.links.append(
                    Link(source=self.page_url, target=clean or self.page_url, fragment=fragment)
                )
            if attr.get("id"):
                self.anchors.add(attr["id"])
            if attr.get("name"):
                self.anchors.add(attr["name"])
        elif tag in {"section", "div", "main", "article", "header", "footer", "h1", "h2", "h3"}:
            if attr.get("id"):
                self.anchors.add(attr["id"])
        elif tag == "title":
            self._in_title = True
        elif tag == "meta" and attr.get("name", "").lower() == "description":
            self.description = attr.get("content") or None
        elif tag == "link" and attr.get("rel", "").lower() == "canonical":
            self.canonical = attr.get("href") or None

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            title = "".join(self._title_parts).strip()
            self.title = title or None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)


def parse_page(page_url: str, body: str) -> PageParser:
    parser = PageParser(page_url)
    parser.feed(body)
    return parser
