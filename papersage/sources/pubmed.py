"""PubMed fetcher via NCBI E-utilities (esearch + efetch).

No key required; an NCBI_API_KEY raises the rate limit from 3 to 10 req/s.
PubMed is biomedical, so this surfaces AI-in-medicine / bioinformatics work.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import requests

from ..models import Paper

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

UA = "PaperSage/1.0 (https://github.com/ekambaranath/PaperSage)"
_HEADERS = {"User-Agent": UA}


def _key_params(api_key: str) -> dict:
    return {"api_key": api_key} if api_key else {}


def _esearch(term: str, lookback_days: int, api_key: str, retmax: int) -> list[str]:
    params = {
        "db": "pubmed",
        "term": term,
        "retmax": retmax,
        "sort": "date",
        "datetype": "pdat",
        "reldate": max(lookback_days, 1),
        "retmode": "json",
    }
    params.update(_key_params(api_key))
    try:
        resp = requests.get(ESEARCH, params=params, headers=_HEADERS, timeout=45)
        resp.raise_for_status()
        return resp.json().get("esearchresult", {}).get("idlist", []) or []
    except (requests.RequestException, ValueError) as exc:
        print(f"[pubmed] esearch '{term}' failed: {exc}")
        return []


def _text(node, path: str) -> str:
    el = node.find(path)
    return "".join(el.itertext()).strip() if el is not None else ""


def _efetch(pmids: list[str], api_key: str) -> list[Paper]:
    if not pmids:
        return []
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
    params.update(_key_params(api_key))
    try:
        resp = requests.get(EFETCH, params=params, headers=_HEADERS, timeout=60)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except (requests.RequestException, ET.ParseError) as exc:
        print(f"[pubmed] efetch failed: {exc}")
        return []

    papers: list[Paper] = []
    for art in root.findall(".//PubmedArticle"):
        title = _text(art, ".//ArticleTitle")
        abstract_parts = [
            "".join(a.itertext()).strip()
            for a in art.findall(".//Abstract/AbstractText")
        ]
        abstract = " ".join(p for p in abstract_parts if p)
        if not title or not abstract:
            continue
        pmid = _text(art, ".//PMID")
        authors = []
        for a in art.findall(".//Author"):
            last = _text(a, "LastName")
            fore = _text(a, "ForeName")
            name = (fore + " " + last).strip()
            if name:
                authors.append(name)
        doi = ""
        for aid in art.findall(".//ArticleId"):
            if aid.get("IdType") == "doi":
                doi = (aid.text or "").strip()
                break
        # Publication date (best-effort).
        published = None
        y = _text(art, ".//PubDate/Year")
        m = _text(art, ".//PubDate/Month") or "1"
        d = _text(art, ".//PubDate/Day") or "1"
        if y:
            months = {
                "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            }
            mi = months.get(m[:3].lower(), None)
            if mi is None:
                try:
                    mi = int(m)
                except ValueError:
                    mi = 1
            try:
                published = datetime(int(y), mi, int(d), tzinfo=timezone.utc)
            except (ValueError, TypeError):
                published = None
        papers.append(
            Paper(
                title=" ".join(title.split()),
                abstract=" ".join(abstract.split()),
                authors=authors,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                source="PubMed",
                published=published,
                doi=doi,
                extra={"pmid": pmid},
            )
        )
    return papers


def fetch(
    keywords: list[str],
    lookback_days: int,
    api_key: str = "",
    max_per_keyword: int = 15,
) -> list[Paper]:
    all_ids: list[str] = []
    seen: set[str] = set()
    # Bias PubMed toward the AI-in-medicine intersection.
    for kw in keywords:
        term = f'({kw}) AND ("artificial intelligence"[tiab] OR "machine learning"[tiab] OR "deep learning"[tiab] OR "large language model"[tiab])'
        ids = _esearch(term, lookback_days, api_key, max_per_keyword)
        for i in ids:
            if i not in seen:
                seen.add(i)
                all_ids.append(i)
        time.sleep(0.4 if api_key else 0.8)

    papers = _efetch(all_ids[:80], api_key)
    print(f"[pubmed] fetched {len(papers)} recent papers")
    return papers
