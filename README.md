# Signal NFX Investor Scraper

Pull targeted investor lists from [Signal NFX](https://signal.nfx.com) - sector-curated, filterable by geography and check size. Output is a clean CSV ready for Clay or Google Sheets.

Signal NFX maintains 200+ curated "top investors in X" lists (EdTech, cybersecurity, climate, fintech, impact, and more). This tool lets you pull any of them, filter to your target geography and check size, and get a structured list with names, firms, LinkedIn URLs, and investment details.

---

## Quickstart with Claude Code

The easiest way to use this is through Claude Code - you describe what you want in plain English and Claude handles the rest.

**1. Clone the repo**
```bash
git clone https://github.com/sahil-valecha/signal-nfx-scraper.git
cd signal-nfx-scraper
```

**2. Install the one optional dependency** (macOS only, for auto-login)
```bash
pip install pycryptodome
```

**3. Open in Claude Code**
```bash
claude
```

**4. Run the skill**
```
/signal-nfx
```

Then just tell Claude what you need:
> *"I want to reach out to investors in the USA who back cybersecurity startups"*

Claude will log you in, find the right Signal NFX lists, scrape them, filter by your criteria, and save a CSV.

---

## What you get

A CSV file with one row per investor:

| Column | Description |
|--------|-------------|
| `name` | Investor full name |
| `first_name` / `last_name` | Split for personalization |
| `signal_profile_url` | Link to their Signal NFX profile |
| `linkedin_url` | LinkedIn profile URL |
| `twitter_url` | Twitter/X profile URL |
| `firm` | Fund or firm name |
| `firm_description` | Short firm description |
| `firm_linkedin_url` | Firm LinkedIn page |
| `firm_url` | Firm website |
| `firm_crunchbase_url` | Firm Crunchbase page |
| `position` | Rank within the Signal NFX list |
| `stages` | Investment stages (Seed, Series A, etc.) |
| `min_investment` | Minimum check size (USD) |
| `max_investment` | Maximum check size (USD) |
| `target_investment` | Target check size (USD) |
| `investment_locations` | Geographies they invest in |
| `source_list` | Which Signal NFX list(s) they appeared in |

---

## Manual usage (no Claude Code)

**See all available investor lists:**
```bash
python scraper.py discover
```

**Scrape a list:**
```bash
python scraper.py scrape --slugs "cybersecurity-seed"
```

**With filters:**
```bash
python scraper.py scrape \
  --slugs "cybersecurity-seed,cybersecurity-series-a" \
  --locations "United States" \
  --min-check 250000 \
  --output cybersecurity-usa-investors.csv
```

**Filter an existing CSV:**
```bash
python scraper.py filter \
  --input raw-investors.csv \
  --locations "Europe" \
  --min-check 500000 \
  --output europe-investors.csv
```

**Re-authenticate:**
```bash
python scraper.py auth --reset
```

---

## Authentication

On first run, the script tries to auto-extract your Signal NFX session from Chrome (macOS only). If that fails, it prompts you to paste your JWT manually:

1. Go to [signal.nfx.com](https://signal.nfx.com) and log in
2. Open DevTools → Application → Cookies → `signal.nfx.com`
3. Copy the value of `SIGNAL_ACCESS_JWT`
4. Paste when prompted

Your JWT is saved locally in `.signal_jwt` so you only need to do this once. If it expires, run `python scraper.py auth --reset`.

You can also set it as an environment variable:
```bash
export SIGNAL_JWT="your-jwt-here"
```

---

## Requirements

- Python 3.11+
- `pycryptodome` (optional - only needed for Chrome auto-auth on macOS)
- A Signal NFX account (free at [signal.nfx.com](https://signal.nfx.com))

---

## Notes

- Signal NFX's data is curated by their team - these are vetted investor lists, not raw scraped data
- Pagination and rate limiting are handled automatically
- Scraping large lists (1000+ investors) takes 1-2 minutes
- Results are deduplicated across multiple lists by default
