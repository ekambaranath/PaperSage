"""Semantic Scholar fetcher via the public Graph API.

No API key is required, but one raises the rate limit. We query the bulk
search endpoint filtered by recency and keyword.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import requests

from ..models import Paper

S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,url,authors,publicationDate,externalIds,year"


UA = "PaperSage/1.0 (https://github.com/ekambaranath/PaperSage)"


def _headers(api_key: str) -> dict:
    headers = {"User-Agent": UA}
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def fetch(
    keywords: list[str],
    lookback_days: int,
    api_key: str = "",
    max_per_keyword: int = 20,
) -> list[Paper]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).date()
    year = datetime.now(timezone.utc).year
    papers: list[Paper] = []
    seen_ids: set[str] = set()

    for kw in keywords:
        params = {
            "query": kw,
            "limit": max_per_keyword,
            "fields": FIELDS,
            "sort": "publicationDate:desc",
            "year": f"{year - 1}-{year}",
        }
        try:
            resp = requests.get(
                S2_SEARCH, params=params, headers=_headers(api_key), timeout=45
            )
            if resp.status_code == 429:
                # Rate limited — back off and skip this keyword this run.
                time.sleep(3)
                continue
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"[s2] '{kw}' failed: {exc}")
            time.sleep(1.5)
            continue

        for item in data.get("data", []) or []:
            pid = item.get("paperId")
            if not pid or pid in seen_ids:
                continue
            pub_date_raw = item.get("publicationDate")
            published = None
            if pub_date_raw:
                try:
                    published = datetime.strptime(pub_date_raw, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                except ValueError:
                    published = None
            # Recency filter (only when we actually have a date).
            if published and published.date() < cutoff:
                continue
            abstract = item.get("abstract") or ""
            if not abstract:
                continue  # skip abstract-less records; nothing to summarize
            seen_ids.add(pid)
            ext = item.get("externalIds") or {}
            authors = [a.get("name", "") for a in (item.get("authors") or [])]
            papers.append(
                Paper(
                    title=" ".join((item.get("title") or "").split()),
                    abstract=" ".join(abstract.split()),
                    authors=[a for a in authors if a],
                    url=item.get("url") or "",
                    source="Semantic Scholar",
                    published=published,
                    doi=(ext.get("DOI") or ""),
                    extra={"paperId": pid},
                )
            )
        # Gentle pacing to respect the shared rate limit.
        time.sleep(1.2)

    print(f"[s2] fetched {len(papers)} recent papers")
    return papers
