# Signal NFX Investor Scraper

Pull a targeted investor list from [Signal NFX](https://signal.nfx.com) using Claude Code. Describe what you need in plain English — Claude handles the rest and outputs a CSV ready for Clay or Google Sheets.

---

## Usage

**1. Clone the repo**
```bash
git clone https://github.com/sahil-valecha/signal-nfx-scraper.git
cd signal-nfx-scraper
```

**2. Open in Claude Code**
```bash
claude
```

**3. Run the skill**
```
/investors
```

Claude will ask what you need, check your setup, log you into Signal NFX, find the right lists, scrape them, and save a CSV to your current folder.

---

## What you need

- [Claude Code](https://claude.ai/code) installed
- Python 3.11+
- A Signal NFX account — free at [signal.nfx.com](https://signal.nfx.com)

---

## What you get

A CSV with one row per investor:

| Column | What it is |
|--------|-----------|
| `name` | Investor full name |
| `first_name` / `last_name` | Split for personalisation |
| `linkedin_url` | LinkedIn profile — ready for Clay enrichment |
| `firm` | Fund or firm name |
| `firm_linkedin_url` | Firm LinkedIn page |
| `firm_url` | Firm website |
| `stages` | Investment stages (Pre-seed, Seed, Series A…) |
| `min_investment` / `max_investment` | Check size in USD |
| `investment_locations` | Geographies they invest in |
| `signal_profile_url` | Their Signal NFX profile |
| `source_list` | Which Signal NFX list(s) they came from |

---

## Manual usage (without Claude Code)

```bash
# See all available investor lists
python scraper.py discover

# Scrape a list
python scraper.py scrape --slugs "cybersecurity-seed"

# With filters
python scraper.py scrape \
  --slugs "cybersecurity-seed,cybersecurity-series-a" \
  --locations "United States" \
  --min-check 250000 \
  --output cybersecurity-usa-investors.csv

# Filter an existing CSV
python scraper.py filter \
  --input raw-investors.csv \
  --locations "Europe" \
  --output europe-investors.csv

# Reset login
python scraper.py auth --reset
```

Install the one optional dependency first (Mac only, for auto-login):
```bash
pip install pycryptodome
```

---

## How login works

On first use, Claude walks you through logging in. On Mac, it tries to pull your session automatically from Chrome. If that doesn't work — or you're on Windows/Linux — it asks you to paste your JWT:

1. Go to [signal.nfx.com](https://signal.nfx.com) in Chrome and log in
2. Open DevTools → Application → Cookies → `signal.nfx.com`
3. Copy the value of `SIGNAL_ACCESS_JWT`
4. Paste it when prompted

Your session is saved locally so you only need to do this once.
