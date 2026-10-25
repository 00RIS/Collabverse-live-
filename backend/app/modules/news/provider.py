from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote_plus
from xml.etree import ElementTree
import re
from urllib.parse import urlparse

import httpx


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _plain_text(value: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(unescape(value))
        return " ".join(parser.parts)
    except Exception:
        return re.sub(r"<[^>]+>", " ", unescape(value)).strip()


def _valid_image_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value.strip())
    return value.strip() if parsed.scheme in {"http", "https"} and parsed.netloc else None


class NewsProvider:
    BASE_URL = (
        "https://news.google.com/rss/search"
    )

    CATEGORY_QUERIES = {
        "technology": "technology",
        "artificial_intelligence": (
            "artificial intelligence AI"
        ),
        "business": "business",
        "finance": "finance markets",
        "marketing": "marketing advertising",
        "startups": "startups entrepreneurship",
        "economy": "economy economic",
        "research": "research science",
        "healthcare": "healthcare health technology",
        "design": "design innovation",
        "law": "law legal technology",
        "education": "education university",
        "cybersecurity": "cybersecurity",
        "data_science": "data science analytics",
        "entrepreneurship": (
            "entrepreneurship founders"
        ),
        "operations": (
            "operations supply chain"
        ),
        "global_affairs": (
            "global affairs geopolitics"
        ),
    }

    def fetch_category(
        self,
        category: str,
        limit: int = 10,
    ) -> list[dict]:

        query = self.CATEGORY_QUERIES.get(
            category,
            category.replace("_", " "),
        )

        url = (
            f"{self.BASE_URL}"
            f"?q={quote_plus(query)}"
            "&hl=en-IN"
            "&gl=IN"
            "&ceid=IN:en"
        )

        try:
            response = httpx.get(
                url,
                timeout=15.0,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 CollabVerse/1.0"
                    )
                },
            )

            response.raise_for_status()

        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"News fetch failed for {category}."
            ) from exc

        try:
            root = ElementTree.fromstring(
                response.text
            )

        except ElementTree.ParseError as exc:
            raise RuntimeError(
                "News provider returned invalid XML."
            ) from exc

        items = root.findall(
            "./channel/item"
        )

        articles = []

        for item in items[:limit]:
            title = (
                item.findtext("title")
                or ""
            ).strip()

            link = (
                item.findtext("link")
                or ""
            ).strip()

            description = (
                item.findtext("description")
                or ""
            ).strip()

            image_url = None
            for child in item.iter():
                if child.tag.rsplit("}", 1)[-1].lower() in {"content", "thumbnail"}:
                    image_url = _valid_image_url(child.attrib.get("url"))
                    if image_url:
                        break
            if image_url is None:
                image_match = re.search(
                    r"<img[^>]+src=[\"']([^\"']+)[\"']",
                    unescape(description),
                    flags=re.IGNORECASE,
                )
                if image_match:
                    image_url = _valid_image_url(image_match.group(1))

            source_element = item.find(
                "source"
            )

            source_name = None

            if source_element is not None:
                source_name = (
                    source_element.text
                    or ""
                ).strip() or None

            published_at = self._parse_date(
                item.findtext("pubDate")
            )

            if not title or not link:
                continue

            articles.append(
                {
                    "title": title,
                    "summary": _plain_text(description),
                    "image_url": image_url,
                    "category": category,
                    "source_name": source_name,
                    "article_url": link,
                    "published_at": published_at,
                }
            )

        return articles

    def _parse_date(
        self,
        value: str | None,
    ) -> datetime | None:

        if not value:
            return None

        try:
            dt = parsedate_to_datetime(
                value
            )

            if dt.tzinfo is None:
                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            return dt

        except Exception:
            return None


news_provider = NewsProvider()
