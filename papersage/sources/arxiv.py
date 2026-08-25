"""arXiv fetcher using the public Atom export API (no key required)."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from dateutil import parser as dateparser

from ..models import Paper

ARXIV_API = "http://export.arxiv.org/api/query"

# arXiv asks all API clients to send a descriptive User-Agent.
UA = "PaperSage/1.0 (https://github.com/ekambaranath/PaperSage)"

# AI-relevant primary categories to bias the search toward.
AI_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG", "cs.MA", "cs.IR", "cs.CV", "stat.ML"]


def _build_query(keywords: list[str]) -> str:
    kw_clause = " OR ".join(f'all:"{k}"' for k in keywords)
    cat_clause = " OR ".join(f"cat:{c}" for c in AI_CATEGORIES)
    return f"({kw_clause}) AND ({cat_clause})"


def fetch(keywords: list[str], lookback_days: int, max_results: int = 60) -> list[Paper]:
    """Fetch recent arXiv papers matching any keyword, sorted by submission date."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    params = {
        "search_query": _build_query(keywords),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "start": 0,
        "max_results": max_results,
    }
    papers: list[Paper] = []
    try:
        resp = requests.get(
            ARXIV_API, params=params, headers={"User-Agent": UA}, timeout=45
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[arxiv] request failed: {exc}")
        return papers

    feed = feedparser.parse(resp.text)
    for entry in feed.entries:
        try:
            published = dateparser.parse(entry.get("published", "")).astimezone(timezone.utc)
        except (ValueError, TypeError, AttributeError):
            published = None
        if published and published < cutoff:
            continue

        doi = entry.get("arxiv_doi", "") or ""
        link = entry.get("link", "")
        authors = [a.get("name", "") for a in entry.get("authors", [])]
        papers.append(
            Paper(
                title=" ".join(entry.get("title", "").split()),
                abstract=" ".join(entry.get("summary", "").split()),
                authors=[a for a in authors if a],
                url=link,
                source="arXiv",
                published=published,
                doi=doi,
                extra={"arxiv_id": entry.get("id", "")},
            )
        )
    # Be polite to the arXiv API.
    time.sleep(1)
    print(f"[arxiv] fetched {len(papers)} recent papers")
    return papers
