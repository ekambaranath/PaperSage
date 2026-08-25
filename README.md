# 📚 PaperSage

**Your personal research assistant that never sleeps.**

PaperSage keeps you up to date with the latest research — without you lifting a finger. Every other day, it goes out and finds the newest papers on the topics you care about, reads through them, writes clear summaries, and emails you a tidy digest. You just open your inbox and read.

It runs entirely on its own for free, so once it's set up, you can forget about it.

---

## What it actually does

Think of PaperSage as a diligent research aide who does the same routine every couple of days:

1. **Goes looking** for brand-new papers across three big research libraries — arXiv, Semantic Scholar, and PubMed.
2. **Filters out the noise** and keeps only the papers that genuinely match your interests.
3. **Reads and summarizes** the best ones — pulling out what the paper is about, what the researchers did, and what they found.
4. **Emails it to you** as a clean, easy-to-read digest, with a full report attached (in both a document format and a PDF).

The result: roughly the ten most relevant new papers, summarized and waiting in your inbox every other morning.

---

## How it works, step by step

PaperSage uses two AI helpers, each doing what it's best at:

- **The fast helper (Gemini)** handles the quick, high-volume work — turning your interests into good search terms, and quickly sorting through everything it finds to pick out the papers worth your time. It's cheap and speedy, perfect for sifting.

- **The careful helper (Ox Alpha)** handles the important part — actually reading each chosen paper and writing an accurate, thorough summary you can trust. This is the one doing the real thinking.

Here's the flow, start to finish:

```
   Your topics of interest
            │
            ▼
   Gemini turns them into smart search terms
            │
            ▼
   Searches arXiv, Semantic Scholar & PubMed
   (only papers from the last couple of days)
            │
            ▼
   Gemini ranks everything and keeps the best ~10
            │
            ▼
   Ox Alpha reads each one and writes a clear summary
            │
            ▼
   📧 A polished digest lands in your inbox
```

---

## What you get in each email

Every digest includes:

- **A short overview** at the top, highlighting the common themes in this batch of papers.
- **A summary card for each paper**, with the title, authors, where it came from, a link to read it, and a clear rundown of what it's about and why it matters.
- **Two attachments** — the full report as a document and as a PDF — so you can save or read them however you like.

Everything is formatted to be easy to skim, even on your phone.

---

## Setting it up (about 5 minutes, one time only)

You only need to do this once. After that, it's fully automatic.

### Step 1: Give it your keys and email details

PaperSage needs a few private details to do its job — an AI access key, and your email login so it can send you the digest. You'll add these safely as "secrets" in the project settings (they stay hidden and encrypted).

Here's what to add:

| What to add | What it is |
| --- | --- |
| **OpenRouter key** | Your access key for the AI, from [openrouter.ai/keys](https://openrouter.ai/keys) |
| **Your Gmail address** | The Gmail account that sends the digest (e.g. `ekambaranath23@gmail.com`) |
| **Gmail app password** | A special 16-character password just for apps — **not** your normal Gmail password |
| **Recipient email** | Where you want the digest delivered |

> **About that Gmail app password:** Google won't let apps use your regular password, so you create a separate one just for this. Turn on 2-Step Verification for your Google account, then go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), create one named "PaperSage", and copy the 16 characters it gives you (no spaces).

### Step 2: Tweak it to your taste (optional)

PaperSage works great out of the box, but you can adjust anything if you want:

| Setting | What it controls | Default |
| --- | --- | --- |
| **Topics** | The subjects it searches for | Agentic AI, AI agents, RAG, and other new AI research |
| **How far back to look** | How recent the papers should be | Last 2 days |
| **How many papers** | Maximum papers per email | 10 |

### Step 3: Turn it on

The schedule is already built in. Just open the project's **Actions** tab and switch it on if asked. Want to see it work right away instead of waiting? Hit **Run** and it'll send you a digest within a minute or two.

---

## When it runs

PaperSage delivers a fresh digest **every other day at 8:00 AM (your time)**.

You can also trigger it manually anytime you want an update on the spot — no need to wait for the schedule. And if you'd like a different time, that's a one-line change in the settings.

---

## Want to try it on your own computer first?

If you'd rather run it yourself before going automatic, you can:

```bash
# Download the project
git clone https://github.com/ekambaranath/PaperSage.git
cd PaperSage

# Install what it needs
pip install -r requirements.txt

# Add your keys
cp .env.example .env      # then open .env and fill in your details

# See what it would send, without actually emailing:
DRY_RUN=1 python main.py

# Send for real:
python main.py
```

---

## Good things to know

- **It won't make things up.** PaperSage only summarizes what's actually written in each paper — it never invents results or numbers.
- **It's resilient.** If one of the research libraries is temporarily down or busy, PaperSage just carries on with whatever it could gather. No crashes, no fuss.
- **No spam.** If there's nothing new worth sending on a given day, it simply stays quiet — no empty emails.

---

*That's it. Set it up once, and let PaperSage keep you effortlessly on top of your field.*
