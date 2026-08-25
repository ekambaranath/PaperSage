"""OpenRouter LLM client plus the two roles PaperSage uses:

* Gemini 2.5 Flash  -> cheap "menial" work: query expansion + relevance ranking.
* Ox Alpha          -> the accuracy-critical work: thorough per-paper summaries
                       and the final synthesized report intro.
"""
from __future__ import annotations

import json
import re

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Config
from .models import Paper


class OpenRouterClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {cfg.openrouter_api_key}",
                "Content-Type": "application/json",
                # Optional attribution headers OpenRouter recommends.
                "HTTP-Referer": "https://github.com/ekambaranath/PaperSage",
                "X-Title": "PaperSage",
            }
        )

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        reraise=True,
    )
    def chat(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = self.session.post(
            f"{self.cfg.openrouter_base_url}/chat/completions",
            data=json.dumps(payload),
            timeout=120,
        )
        if resp.status_code >= 400:
            # Surface the API's error body to make debugging easy.
            raise RuntimeError(f"OpenRouter {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected OpenRouter response: {data}") from exc


def _extract_json(text: str):
    """Pull the first JSON object/array out of a model response."""
    text = text.strip()
    # Strip markdown code fences if present.
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


# --------------------------------------------------------------------------- #
# Gemini role 1: expand the user's topics into concrete search keywords.
# --------------------------------------------------------------------------- #
def expand_queries(client: OpenRouterClient, topics: list[str]) -> list[str]:
    prompt = (
        "You generate search keywords for academic paper databases "
        "(arXiv, Semantic Scholar, PubMed).\n"
        f"The user's research interests are: {', '.join(topics)}.\n\n"
        "Produce 10-14 concise search phrases (2-5 words each) that together give "
        "broad but precise coverage of these interests and closely related, "
        "cutting-edge subtopics. Favor terminology researchers actually use in "
        "paper titles/abstracts. Return ONLY a JSON array of strings."
    )
    try:
        raw = client.chat(
            client.cfg.triage_model,
            [{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=800,
        )
        data = _extract_json(raw)
        if isinstance(data, list):
            queries = [str(x).strip() for x in data if str(x).strip()]
            if queries:
                return queries[:14]
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        print(f"[gemini] query expansion failed, using topics directly: {exc}")
    return topics


# --------------------------------------------------------------------------- #
# Gemini role 2: score candidate papers for relevance, then we rank + cut.
# --------------------------------------------------------------------------- #
def rank_papers(
    client: OpenRouterClient,
    papers: list[Paper],
    topics: list[str],
    top_k: int,
) -> list[Paper]:
    if not papers:
        return []

    catalog = [
        {
            "i": idx,
            "title": p.title,
            "abstract": (p.abstract[:600] + "…") if len(p.abstract) > 600 else p.abstract,
            "source": p.source,
        }
        for idx, p in enumerate(papers)
    ]
    prompt = (
        "You are triaging newly published papers for a researcher.\n"
        f"Their interests: {', '.join(topics)}.\n\n"
        "For EACH paper below, rate relevance 0-100 (100 = squarely on-topic and "
        "novel/important; 0 = unrelated). Be discerning — reserve high scores for "
        "genuinely relevant, substantive work.\n"
        "Return ONLY a JSON array of objects: "
        '[{"i": <index>, "score": <0-100>, "reason": "<=15 words"}].\n\n'
        f"PAPERS:\n{json.dumps(catalog, ensure_ascii=False)}"
    )
    scores: dict[int, tuple[float, str]] = {}
    try:
        raw = client.chat(
            client.cfg.triage_model,
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4000,
        )
        data = _extract_json(raw)
        if isinstance(data, list):
            for item in data:
                try:
                    i = int(item["i"])
                    scores[i] = (float(item.get("score", 0)), str(item.get("reason", "")))
                except (KeyError, ValueError, TypeError):
                    continue
    except Exception as exc:  # noqa: BLE001
        print(f"[gemini] ranking failed, falling back to recency order: {exc}")

    for idx, p in enumerate(papers):
        score, reason = scores.get(idx, (0.0, ""))
        p.relevance = score
        p.relevance_reason = reason

    # If ranking produced nothing usable, keep original (recency) order.
    if not scores:
        return papers[:top_k]

    ranked = sorted(papers, key=lambda p: p.relevance, reverse=True)
    # Drop clearly irrelevant items even if we have fewer than top_k.
    ranked = [p for p in ranked if p.relevance >= 35] or ranked
    return ranked[:top_k]


# --------------------------------------------------------------------------- #
# Ox Alpha role 1: thorough per-paper summary (accuracy-critical).
# --------------------------------------------------------------------------- #
SUMMARY_SYSTEM = (
    "You are a meticulous research analyst. You write thorough, faithful summaries "
    "of academic papers from their title and abstract, never inventing results or "
    "numbers not present in the source. If the abstract lacks a detail, say so rather "
    "than guessing."
)


def summarize_paper(client: OpenRouterClient, paper: Paper) -> str:
    user = (
        f"Title: {paper.title}\n"
        f"Authors: {paper.authors_str}\n"
        f"Source: {paper.source} ({paper.published_str})\n"
        f"Abstract:\n{paper.abstract}\n\n"
        "Write a thorough summary in Markdown with EXACTLY these bold labels, each on "
        "its own line, no headings:\n"
        "**Problem:** what gap or question this addresses.\n"
        "**Approach:** the method/architecture/technique, in concrete terms.\n"
        "**Key findings:** the main results, including any specific numbers or "
        "comparisons stated in the abstract.\n"
        "**Why it matters:** the significance for the field and practitioners.\n"
        "**Caveats:** stated limitations, or note if none are given.\n\n"
        "Be complete but tight — capture everything important in the abstract without "
        "padding. Do not fabricate details beyond the abstract."
    )
    try:
        return client.chat(
            client.cfg.summarizer_model,
            [
                {"role": "system", "content": SUMMARY_SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=1200,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[oxalpha] summary failed for '{paper.title[:60]}': {exc}")
        # Fall back to the raw abstract so the digest is never empty.
        return f"**Abstract (summary unavailable):** {paper.abstract}"


# --------------------------------------------------------------------------- #
# Ox Alpha role 2: a short editor's overview tying the batch together.
# --------------------------------------------------------------------------- #
def write_overview(client: OpenRouterClient, papers: list[Paper], topics: list[str]) -> str:
    listing = "\n".join(
        f"- [{p.source}] {p.title}" for p in papers
    )
    user = (
        f"A researcher tracks these interests: {', '.join(topics)}.\n"
        f"Today's digest contains these {len(papers)} papers:\n{listing}\n\n"
        "Write a concise 3-5 sentence editor's overview: the notable themes or "
        "throughlines across this batch and what stands out. Plain prose, no lists, "
        "no preamble like 'Here is'. Do not invent findings — speak only to the topics "
        "and titles shown."
    )
    try:
        return client.chat(
            client.cfg.summarizer_model,
            [{"role": "user", "content": user}],
            temperature=0.4,
            max_tokens=500,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[oxalpha] overview failed: {exc}")
        return ""
