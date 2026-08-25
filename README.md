# 📚 PaperSage

**PaperSage** is an automated research-paper agent. Every alternate day it fetches
the latest papers from **arXiv**, **Semantic Scholar**, and **PubMed**, triages and
ranks them for relevance to your interests, writes thorough summaries, and emails you
a clean digest — with a full report attached as **Markdown and PDF**.

It runs for free on **GitHub Actions**, so once it's set up you never have to touch it.

---

## How it works

```
   your topics
        │
        ▼
 ┌──────────────┐   query phrases   ┌───────────────────────────────┐
 │  Gemini 2.5  │ ────────────────▶ │  arXiv · Semantic Scholar ·   │
 │    Flash     │                   │           PubMed              │
 │ (cheap prep) │ ◀──── candidates ─│   (last 2 days, deduped)      │
 └──────────────┘                   └───────────────────────────────┘
        │ ranks & keeps top ~10
        ▼
 ┌──────────────┐  thorough summaries + editor's overview
 │   Ox Alpha   │ ─────────────────────────────────────────▶  HTML email
 │ (accurate)   │                                             + .md + .pdf
 └──────────────┘                                                  │
                                                                   ▼
                                                        📧 your inbox
```

* **Gemini 2.5 Flash** does the cheap, high-volume work: expanding your topics into
  good search phrases and scoring every fetched paper for relevance.
* **Ox Alpha** (`stealth/ox-alpha`) does the accuracy-critical work: writing the
  faithful, detailed per-paper summaries and the editor's overview.

Both models are called through a single **OpenRouter** API key.

---

## Setup (one time, ~5 minutes)

### 1. Add repository secrets

Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | What it is |
| --- | --- |
| `OPENROUTER_API_KEY` | Your key from [openrouter.ai/keys](https://openrouter.ai/keys) |
| `GMAIL_ADDRESS` | The Gmail that sends the digest (e.g. `ekambaranath23@gmail.com`) |
| `GMAIL_APP_PASSWORD` | A 16-character [Google App Password](https://myaccount.google.com/apppasswords) — **not** your normal password |
| `RECIPIENT_EMAIL` | Where the digest is delivered |

> **Getting the Gmail App Password:** enable 2-Step Verification on your Google
> account, then visit [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords),
> create a password named "PaperSage", and paste the 16 characters (no spaces) as
> `GMAIL_APP_PASSWORD`.

Optional secrets (leave unset if you don't have them — they just raise rate limits):
`NCBI_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`.

### 2. (Optional) Customize behavior

Under **Settings → Secrets and variables → Actions → Variables**, you can add any of:

| Variable | Default |
| --- | --- |
| `PAPERSAGE_TOPICS` | `Agentic AI, AI agents, tool use, LLM reasoning, retrieval-augmented generation (RAG), multi-agent systems, new AI research` |
| `SUMMARIZER_MODEL` | `stealth/ox-alpha` |
| `TRIAGE_MODEL` | `google/gemini-2.5-flash` |
| `LOOKBACK_DAYS` | `2` |
| `MAX_PAPERS` | `10` |

### 3. Enable the workflow

The schedule is already configured in `.github/workflows/digest.yml`. To confirm it's
active, open the **Actions** tab and enable workflows if prompted. You can run it
immediately with **Actions → PaperSage Digest → Run workflow** (set `force = true` to
bypass the alternate-day gate).

---

## Schedule

* Fires daily at **02:30 UTC = 08:00 IST**.
* A parity gate runs it on **alternate days only** (even day-of-year), so you get a
  digest every other day.
* Manual runs via **Run workflow** always work; pass `force = true` to run on an off day.

To change the time, edit the `cron` line in `.github/workflows/digest.yml`
(GitHub cron is in **UTC**).

---

## Run it locally

```bash
git clone https://github.com/ekambaranath/PaperSage.git
cd PaperSage
pip install -r requirements.txt
cp .env.example .env      # then fill in your keys

# Preview without sending an email:
DRY_RUN=1 python main.py

# Actually send:
python main.py
```

---

## Project layout

```
PaperSage/
├── main.py                       # entrypoint
├── requirements.txt
├── .env.example                  # copy to .env for local runs
├── .github/workflows/digest.yml  # every-other-day cron
└── papersage/
    ├── config.py                 # env-based configuration
    ├── models.py                 # Paper data model
    ├── llm.py                    # OpenRouter: Gemini triage + Ox Alpha summaries
    ├── pipeline.py               # fetch → rank → summarize → deliver
    ├── report.py                 # HTML email + Markdown + PDF
    ├── emailer.py                # Gmail SMTP delivery
    └── sources/
        ├── arxiv.py
        ├── semantic_scholar.py
        └── pubmed.py
```

---

## Notes

* Summaries are written **only from paper abstracts** — the agent is instructed never
  to invent results not present in the source.
* If a source API is down or rate-limited, PaperSage degrades gracefully and continues
  with whatever it could fetch.
* If no papers match in the window, no email is sent (nothing to report).
