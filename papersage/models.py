"""Shared data structures for PaperSage."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Paper:
    title: str
    abstract: str
    authors: list[str]
    url: str
    source: str  # "arXiv" | "Semantic Scholar" | "PubMed"
    published: Optional[datetime] = None
    doi: str = ""
    extra: dict = field(default_factory=dict)

    # Populated later in the pipeline.
    relevance: float = 0.0
    relevance_reason: str = ""
    summary: str = ""

    @property
    def published_str(self) -> str:
        return self.published.strftime("%Y-%m-%d") if self.published else "n/a"

    @property
    def authors_str(self) -> str:
        if not self.authors:
            return "Unknown authors"
        if len(self.authors) <= 6:
            return ", ".join(self.authors)
        return ", ".join(self.authors[:6]) + f", +{len(self.authors) - 6} more"

    def dedup_key(self) -> str:
        """A best-effort identity for cross-source de-duplication."""
        if self.doi:
            return "doi:" + self.doi.lower().strip()
        norm = re.sub(r"[^a-z0-9]+", " ", self.title.lower()).strip()
        return "title:" + norm
