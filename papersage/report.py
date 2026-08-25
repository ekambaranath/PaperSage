"""Build the digest in three forms: HTML email body, Markdown report, PDF report."""
from __future__ import annotations

import io
from datetime import datetime, timezone

import markdown as md

from .models import Paper

BRAND = "PaperSage"


def _md_inline_to_html(text: str) -> str:
    """Render a small Markdown fragment (bold labels etc.) to inline HTML."""
    return md.markdown(text, extensions=["extra", "nl2br"])


def build_markdown(papers: list[Paper], overview: str, topics: list[str]) -> str:
    today = datetime.now(timezone.utc).astimezone().strftime("%A, %d %B %Y")
    lines = [
        f"# {BRAND} — Research Digest",
        f"*{today}*",
        "",
        f"**Tracking:** {', '.join(topics)}",
        f"**Papers in this issue:** {len(papers)}",
        "",
    ]
    if overview:
        lines += ["## Editor's Overview", "", overview, ""]
    lines += ["---", ""]
    for i, p in enumerate(papers, 1):
        lines += [
            f"## {i}. {p.title}",
            "",
            f"**Source:** {p.source}  |  **Published:** {p.published_str}  "
            f"|  **Relevance:** {int(p.relevance)}/100",
            f"**Authors:** {p.authors_str}",
            f"**Link:** {p.url}" + (f"  |  **DOI:** {p.doi}" if p.doi else ""),
            "",
            p.summary or p.abstract,
            "",
            "---",
            "",
        ]
    lines += [f"*Generated automatically by {BRAND}.*"]
    return "\n".join(lines)


def build_html(papers: list[Paper], overview: str, topics: list[str]) -> str:
    today = datetime.now(timezone.utc).astimezone().strftime("%A, %d %B %Y")
    source_colors = {
        "arXiv": "#b31b1b",
        "Semantic Scholar": "#1857b6",
        "PubMed": "#20639b",
    }

    cards = []
    for i, p in enumerate(papers, 1):
        badge_color = source_colors.get(p.source, "#555")
        summary_html = _md_inline_to_html(p.summary or p.abstract)
        doi_html = (
            f' &nbsp;·&nbsp; <span style="color:#888">DOI:</span> {p.doi}'
            if p.doi else ""
        )
        cards.append(f"""
        <tr><td style="padding:0 0 22px 0;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 style="background:#ffffff;border:1px solid #e6e8eb;border-radius:12px;overflow:hidden;">
            <tr><td style="padding:20px 22px 6px 22px;">
              <span style="display:inline-block;background:{badge_color};color:#fff;
                    font-size:11px;font-weight:600;letter-spacing:.03em;padding:3px 9px;
                    border-radius:20px;text-transform:uppercase;">{p.source}</span>
              <span style="display:inline-block;background:#eef1f5;color:#334;font-size:11px;
                    font-weight:600;padding:3px 9px;border-radius:20px;margin-left:6px;">
                    {int(p.relevance)}/100</span>
              <span style="color:#98a2b3;font-size:12px;margin-left:6px;">{p.published_str}</span>
              <h2 style="margin:10px 0 4px 0;font-size:18px;line-height:1.35;color:#101828;">
                {i}. {p.title}
              </h2>
              <div style="color:#667085;font-size:13px;margin-bottom:2px;">{p.authors_str}</div>
              <div style="font-size:13px;margin:2px 0 12px 0;">
                <a href="{p.url}" style="color:{badge_color};text-decoration:none;font-weight:600;">
                   Read paper →</a>{doi_html}
              </div>
              <div style="color:#344054;font-size:14px;line-height:1.6;">{summary_html}</div>
            </td></tr>
          </table>
        </td></tr>""")

    overview_block = ""
    if overview:
        overview_block = f"""
        <tr><td style="padding:0 0 22px 0;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 style="background:#101828;border-radius:12px;">
            <tr><td style="padding:20px 22px;">
              <div style="color:#98a2b3;font-size:11px;font-weight:700;letter-spacing:.08em;
                   text-transform:uppercase;margin-bottom:8px;">Editor's Overview</div>
              <div style="color:#e6e8eb;font-size:15px;line-height:1.6;">{overview}</div>
            </td></tr>
          </table>
        </td></tr>"""

    topics_str = ", ".join(topics)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f2f4f7;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f2f4f7;">
    <tr><td align="center" style="padding:28px 14px;">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0"
             style="max-width:640px;width:100%;">
        <tr><td style="padding:0 0 20px 0;text-align:center;">
          <div style="font-size:26px;font-weight:800;color:#101828;letter-spacing:-.02em;">
            📚 {BRAND}</div>
          <div style="color:#667085;font-size:13px;margin-top:4px;">Research digest · {today}</div>
          <div style="color:#98a2b3;font-size:12px;margin-top:8px;">Tracking: {topics_str}</div>
        </td></tr>
        {overview_block}
        {''.join(cards)}
        <tr><td style="padding:8px 0 0 0;text-align:center;color:#98a2b3;font-size:12px;line-height:1.6;">
          {len(papers)} papers · sourced from arXiv, Semantic Scholar & PubMed<br>
          Summarized by Ox Alpha · triaged by Gemini · delivered by {BRAND}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def build_pdf(html_report_md: str) -> bytes | None:
    """Render the Markdown report to a PDF. Returns None if rendering fails."""
    try:
        from xhtml2pdf import pisa
    except ImportError:
        print("[report] xhtml2pdf not installed; skipping PDF")
        return None

    body = md.markdown(html_report_md, extensions=["extra"])
    styled = f"""<html><head><style>
      @page {{ margin: 1.6cm; }}
      body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt; color:#222; line-height:1.5; }}
      h1 {{ font-size: 20pt; color:#101828; }}
      h2 {{ font-size: 13pt; color:#1a2b4a; margin-top:16px; border-bottom:1px solid #ddd; padding-bottom:3px; }}
      strong {{ color:#101828; }}
      hr {{ border:none; border-top:1px solid #e0e0e0; margin:10px 0; }}
      a {{ color:#1857b6; text-decoration:none; }}
      em {{ color:#667085; }}
    </style></head><body>{body}</body></html>"""

    out = io.BytesIO()
    try:
        result = pisa.CreatePDF(src=styled, dest=out)
        if result.err:
            print("[report] PDF rendering reported errors")
            return None
        return out.getvalue()
    except Exception as exc:  # noqa: BLE001
        print(f"[report] PDF rendering failed: {exc}")
        return None
