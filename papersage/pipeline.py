"""End-to-end orchestration: fetch -> dedupe -> triage/rank -> summarize -> deliver."""
from __future__ import annotations

from datetime import datetime, timezone

from . import llm
from .config import Config
from .emailer import send_digest
from .models import Paper
from .report import build_html, build_markdown, build_pdf
from .sources import arxiv, pubmed, semantic_scholar


def _dedupe(papers: list[Paper]) -> list[Paper]:
    seen: dict[str, Paper] = {}
    for p in papers:
        key = p.dedup_key()
        # Prefer the record with the longer abstract if duplicated.
        if key not in seen or len(p.abstract) > len(seen[key].abstract):
            seen[key] = p
    return list(seen.values())


def run(cfg: Config) -> dict:
    problems = cfg.validate()
    if problems:
        raise SystemExit("Configuration errors:\n  - " + "\n  - ".join(problems))

    client = llm.OpenRouterClient(cfg)
    topics = cfg.topics
    print(f"[run] topics: {topics}")

    # 1. Gemini expands topics into concrete search phrases.
    queries = llm.expand_queries(client, topics)
    print(f"[run] search phrases ({len(queries)}): {queries}")

    # 2. Fetch from all three sources (each degrades gracefully on failure).
    candidates: list[Paper] = []
    candidates += arxiv.fetch(queries, cfg.lookback_days)
    candidates += semantic_scholar.fetch(
        queries, cfg.lookback_days, api_key=cfg.semantic_scholar_api_key
    )
    candidates += pubmed.fetch(queries, cfg.lookback_days, api_key=cfg.ncbi_api_key)

    # 3. Dedupe across sources.
    candidates = _dedupe(candidates)
    print(f"[run] {len(candidates)} unique candidates after dedupe")

    if not candidates:
        print("[run] no papers found in the window — nothing to send.")
        return {"papers": 0, "sent": False}

    # Cap candidates before the (single) ranking call.
    candidates = candidates[: cfg.max_candidates]

    # 4. Gemini ranks; keep the top N.
    top = llm.rank_papers(client, candidates, topics, cfg.max_papers)
    print(f"[run] {len(top)} papers selected for summarization")

    # 5. Ox Alpha writes thorough summaries.
    for i, p in enumerate(top, 1):
        print(f"[run] summarizing {i}/{len(top)}: {p.title[:70]}")
        p.summary = llm.summarize_paper(client, p)

    # 6. Ox Alpha writes the editor's overview.
    overview = llm.write_overview(client, top, topics)

    # 7. Build outputs.
    markdown_report = build_markdown(top, overview, topics)
    html_body = build_html(top, overview, topics)
    pdf_bytes = build_pdf(markdown_report)

    stamp = datetime.now(timezone.utc).astimezone().strftime("%d %b %Y")
    subject = f"📚 PaperSage Digest — {len(top)} new papers ({stamp})"

    # 8. Deliver.
    if cfg.dry_run:
        print("\n===== DRY RUN: report preview =====\n")
        print(markdown_report)
        print("\n===== end preview (email not sent) =====")
        return {"papers": len(top), "sent": False, "dry_run": True}

    send_digest(cfg, subject, html_body, markdown_report, pdf_bytes)
    return {"papers": len(top), "sent": True}
