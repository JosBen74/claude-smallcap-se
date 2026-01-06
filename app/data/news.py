"""Nyhetshämtning för svenska aktier."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import requests


@dataclass
class NewsItem:
    """En nyhetsartikel."""

    title: str
    url: str
    source: str
    published: datetime
    summary: Optional[str] = None
    company: Optional[str] = None
    ticker: Optional[str] = None
    is_regulatory: bool = False


class NewsAggregator:
    """Aggregerar nyheter från flera svenska källor."""

    # RSS-källor
    RSS_SOURCES = {
        "avanza_blogg": {
            "url": "https://blogg.avanza.se/feed/",
            "name": "Avanza Blogg",
            "enabled": True,
        },
        "di_rss": {
            "url": "https://digital.di.se/rss",
            "name": "Dagens Industri",
            "enabled": True,
        },
        # Inaktiverade - returnerar 404
        "svd_naringsliv": {
            "url": "https://www.svd.se/feed/naringsliv.rss",
            "name": "SvD Näringsliv",
            "enabled": False,
        },
        "affarsvarlden": {
            "url": "https://www.affarsvarlden.se/feed",
            "name": "Affärsvärlden",
            "enabled": False,
        },
    }

    # Företagsnamn till ticker-mappning (vanliga small-cap)
    COMPANY_TICKER_MAP = {
        "embracer": "EMBRAC-B",
        "sinch": "SINCH",
        "boozt": "BOOZT",
        "storytel": "STORY-B",
        "stillfront": "SF",
        "paradox": "PDX",
        "starbreeze": "STAR-B",
        "thunderful": "THUNDR",
        "enad global": "ENAD",
        "g5 entertainment": "G5EN",
        "mips": "MIPS",
        "vitrolife": "VITR",
        "surgical science": "SUS",
        "cellink": "BICO",
        "bico": "BICO",
        "nibe": "NIBE-B",
        "hexagon": "HEXA-B",
        "assa abloy": "ASSA-B",
        "alfa laval": "ALFA",
        "electrolux": "ELUX-B",
        "ericsson": "ERIC-B",
        "volvo": "VOLV-B",
        "saab": "SAAB-B",
        "sandvik": "SAND",
        "atlas copco": "ATCO-A",
        "seb": "SEB-A",
        "handelsbanken": "SHB-A",
        "swedbank": "SWED-A",
        "nordea": "NDA-SE",
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; ClaudeSmallCapSE/1.0)"
        })

    def fetch_all(self, days: int = 7) -> list[NewsItem]:
        """Hämta nyheter från alla aktiverade källor."""
        all_news = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for source_id, source_config in self.RSS_SOURCES.items():
            if not source_config.get("enabled", False):
                continue

            try:
                news = self._fetch_rss(
                    url=source_config["url"],
                    source_name=source_config["name"],
                    cutoff_date=cutoff_date,
                )
                all_news.extend(news)
            except Exception as e:
                print(f"Fel vid hämtning från {source_config['name']}: {e}")

        # Sortera efter datum (nyast först)
        all_news.sort(key=lambda x: x.published, reverse=True)

        return all_news

    def fetch_for_tickers(
        self,
        tickers: list[str],
        days: int = 7
    ) -> dict[str, list[NewsItem]]:
        """Hämta nyheter filtrerade per ticker."""
        all_news = self.fetch_all(days=days)

        result = {ticker: [] for ticker in tickers}

        for news_item in all_news:
            # Försök matcha mot tickers
            matched_ticker = self._match_ticker(news_item, tickers)
            if matched_ticker:
                news_item.ticker = matched_ticker
                result[matched_ticker].append(news_item)

        return result

    def fetch_market_news(self, days: int = 7, limit: int = 20) -> list[NewsItem]:
        """Hämta generella marknadsnyheter."""
        all_news = self.fetch_all(days=days)

        # Filtrera bort företagsspecifika nyheter
        market_keywords = [
            "börsen", "index", "omxs", "ränta", "inflation",
            "konjunktur", "fed", "riksbank", "ecb", "marknad",
            "small cap", "large cap", "sektor", "bransch",
        ]

        market_news = []
        for news in all_news:
            title_lower = news.title.lower()
            if any(kw in title_lower for kw in market_keywords):
                market_news.append(news)

        return market_news[:limit]

    def _fetch_rss(
        self,
        url: str,
        source_name: str,
        cutoff_date: datetime,
    ) -> list[NewsItem]:
        """Hämta och parsa RSS-feed."""
        news_items = []

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            root = ET.fromstring(response.content)

            # Hantera olika RSS-format
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

            for item in items:
                news_item = self._parse_rss_item(item, source_name)
                if news_item and news_item.published >= cutoff_date:
                    news_items.append(news_item)

        except requests.RequestException as e:
            print(f"HTTP-fel för {url}: {e}")
        except ET.ParseError as e:
            print(f"XML-parsningsfel för {url}: {e}")

        return news_items

    def _parse_rss_item(self, item: ET.Element, source_name: str) -> Optional[NewsItem]:
        """Parsa ett RSS-item till NewsItem."""
        try:
            # RSS 2.0 format
            title = self._get_text(item, "title")
            link = self._get_text(item, "link")
            pub_date = self._get_text(item, "pubDate")
            description = self._get_text(item, "description")

            # Atom format fallback
            if not title:
                title = self._get_text(item, "{http://www.w3.org/2005/Atom}title")
            if not link:
                link_elem = item.find("{http://www.w3.org/2005/Atom}link")
                if link_elem is not None:
                    link = link_elem.get("href", "")
            if not pub_date:
                pub_date = self._get_text(item, "{http://www.w3.org/2005/Atom}published")
            if not description:
                description = self._get_text(item, "{http://www.w3.org/2005/Atom}summary")

            if not title or not link:
                return None

            # Parsa datum
            published = self._parse_date(pub_date) if pub_date else datetime.now()

            # Rensa HTML från summary
            if description:
                description = re.sub(r"<[^>]+>", "", description)[:300]

            return NewsItem(
                title=title,
                url=link,
                source=source_name,
                published=published,
                summary=description,
            )

        except Exception:
            return None

    def _get_text(self, element: ET.Element, tag: str) -> str:
        """Hämta text från XML-element."""
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else ""

    def _parse_date(self, date_str: str) -> datetime:
        """Parsa olika datumformat."""
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 822
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z",        # ISO 8601
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=None)
            except ValueError:
                continue

        return datetime.now()

    def _match_ticker(self, news: NewsItem, tickers: list[str]) -> Optional[str]:
        """Matcha nyhet mot ticker."""
        text = f"{news.title} {news.summary or ''}".lower()

        # Direkt ticker-match
        for ticker in tickers:
            ticker_lower = ticker.lower().replace("-", " ").replace("_", " ")
            if ticker_lower in text:
                return ticker

        # Företagsnamn till ticker
        for company, ticker in self.COMPANY_TICKER_MAP.items():
            if ticker in tickers and company in text:
                return ticker

        return None


def get_news_summary(tickers: list[str], days: int = 7) -> str:
    """Hämta nyhetssammanfattning för Claude-prompten."""
    aggregator = NewsAggregator()

    # Hämta företagsspecifika nyheter
    ticker_news = aggregator.fetch_for_tickers(tickers, days=days)

    # Hämta marknadsnyheter
    market_news = aggregator.fetch_market_news(days=days, limit=10)

    lines = ["## Nyheter senaste veckan\n"]

    # Marknadsnyheter
    if market_news:
        lines.append("### Marknad & makro")
        for news in market_news[:5]:
            lines.append(f"- **{news.title}** ({news.source}, {news.published.strftime('%Y-%m-%d')})")
        lines.append("")

    # Företagsspecifika nyheter
    has_company_news = False
    for ticker, news_list in ticker_news.items():
        if news_list:
            has_company_news = True
            lines.append(f"### {ticker}")
            for news in news_list[:3]:
                lines.append(f"- {news.title} ({news.published.strftime('%Y-%m-%d')})")
            lines.append("")

    if not has_company_news and not market_news:
        lines.append("*Inga relevanta nyheter hittades denna vecka.*")

    return "\n".join(lines)
