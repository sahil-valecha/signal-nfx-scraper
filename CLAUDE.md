# Signal NFX Scraper — Claude Rules

This repo is a tool for pulling targeted investor lists from Signal NFX. Read this before doing anything.

---

## What this repo does

Scrapes Signal NFX's curated investor lists via their GraphQL API. Outputs a CSV with investor names, firms, LinkedIn URLs, check sizes, stages, and locations. The CSV is ready for Clay or Google Sheets.

---

## Always follow the skill protocol

When a user wants to pull investor data, always use the `/signal-nfx` skill. Do not improvise a different approach. The skill encodes hard-won knowledge about what works and what breaks.

---

## Hard rules — never break these

**Auth:**
- The cookie is named `SIGNAL_ACCESS_JWT` — not `token`, not `nfx_token`, not `session`
- Always copy the Chrome Cookies SQLite DB to a temp file before reading — Chrome locks it while running
- Auto-auth only works on macOS — Windows and Linux users must use manual JWT paste

**HTTP:**
- Always use `urllib.request` — never `requests` or `httpx`. Cloudflare blocks non-stdlib HTTP libraries
- Always set `Origin: https://signal.nfx.com` and `Referer: https://signal.nfx.com/` headers on API calls

**GraphQL:**
- The field is `scored_investors` — not `investors` (does not exist)
- Do not query: `person.twitter`, `person.website`, `person.photo_url`, `person.location`, `firm.website_url`, `firm.website`, `node.investment_themes`, `node.investment_stages`, `node.sectors`, `node.tags`, `node.score` — none of these exist in the schema
- Always paginate using `pageInfo.hasNextPage` + `endCursor` — never assume one page is enough

**Slugs:**
- Signal NFX URL slugs and API slugs are different formats
  - URL: `/investor-lists/top-cybersecurity-seed-investors`
  - API: `cybersecurity-seed` (strip `top-` prefix and `-investors` suffix)
- Always run `discover` to get valid slugs — never guess or construct slugs manually

**Filtering:**
- Location filter uses exact string matching against the `investment_locations` field
- "USA" will return 0 results — use `"United States"`
- "UK" will return 0 results — use `"United Kingdom"`
- Always inspect raw location values if a filter returns 0 rows

---

## When something breaks

See the troubleshooting section in `.claude/commands/signal-nfx.md`. Every known failure mode is documented there with the fix. Check it before trying anything else.

---

## What not to do

- Do not modify `scraper.py` to use the `requests` library
- Do not add fields to the GraphQL query that aren't in the known-working list
- Do not skip the `discover` step and hardcode slugs
- Do not tell the user to paste the full cookie header — they only need the `SIGNAL_ACCESS_JWT` value
- Do not run a scrape without confirming the slug list with the user first
