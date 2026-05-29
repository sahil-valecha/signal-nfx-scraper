# Signal NFX Investor List Builder

Pull a targeted investor list from Signal NFX. Follow these steps in order. Do not skip steps. Do not proceed past a checkpoint until it passes.

---

## STEP 0 — Prerequisites check

Run this before anything else:

```bash
python --version
```

If it fails or returns Python 2.x:
- Mac: `brew install python@3.11` or download from python.org
- Windows: download from python.org
- Tell the user to restart their terminal after installing, then re-run `/signal-nfx`
- Do not proceed until `python --version` returns 3.11 or higher

Then check pycryptodome (needed for auto-login on Mac):
```bash
python -c "import Crypto; print('pycryptodome ok')"
```

If it fails:
```bash
pip install pycryptodome
```

If `pip` itself isn't found: try `pip3 install pycryptodome`.

If install fails due to permissions: try `pip install --user pycryptodome`.

Note: pycryptodome is only needed for auto-login on Mac. If the user is on Windows or Linux, skip this and tell them they'll paste their JWT manually in the auth step — that's fine.

**Checkpoint:** Python 3.11+ confirmed. Move to Step 1.

---

## STEP 1 — Intake

Ask the user these four questions. Get answers before doing anything else.

1. **Sector / thesis** — what type of investors? (e.g. cybersecurity, EdTech, climate, fintech, B2B SaaS, impact)
2. **Geography** — which countries or regions? (e.g. USA, Europe, UK, APAC, Global)
3. **Stage** — what stage? (pre-seed, seed, Series A, or any)
4. **Check size** — any preference? (e.g. "$250k–$2M" or "doesn't matter")

If the user already gave some of this in their message, confirm it rather than re-asking. Once you have all four, summarise back to them in one line and ask them to confirm before proceeding.

Example confirmation:
> "Got it - seed-stage cybersecurity investors in the USA, checks $250k–$5M. Proceeding to check your login."

---

## STEP 2 — Authentication

**Run:**
```bash
python scraper.py auth
```

**What to expect:**
- If a cached JWT exists and is valid: prints confirmation, move to Step 3
- If no cache or expired: move to the auth flow below

**Auth flow:**

On macOS, the script auto-extracts the JWT from Chrome. Run:
```bash
pip install pycryptodome
python scraper.py auth --reset
```

If that succeeds: move to Step 3.

If it fails: use manual JWT paste.

**Manual JWT paste (all platforms):**
Tell the user:
1. Open Chrome and go to [signal.nfx.com](https://signal.nfx.com) — log in if needed
2. Open DevTools: `Cmd+Option+I` on Mac, `F12` on Windows
3. Click the **Application** tab
4. In the left sidebar: Cookies → `https://signal.nfx.com`
5. Find the cookie named exactly **`SIGNAL_ACCESS_JWT`**
6. Click it and copy the full value from the bottom panel (it's a long string starting with `eyJ`)
7. Paste it when the script prompts you

Then run:
```bash
python scraper.py auth --reset
```

**Checkpoint:** Do not proceed until `python scraper.py auth` runs without error.

---

### Auth troubleshooting

**"Cookie not found in Chrome"**
→ The user isn't logged into Signal NFX in Chrome, or they're using a different browser.
Fix: open Chrome (not Safari, not Firefox), go to signal.nfx.com, log in, then retry.

**"Could not read Chrome Safe Storage key"**
→ macOS Keychain access issue.
Fix: skip auto-auth entirely. Run `python scraper.py auth --reset` and use manual JWT paste instead.

**"pycryptodome not found" or ImportError on Crypto**
→ Wrong package installed. `crypto` and `pycrypto` are not the same as `pycryptodome`.
Fix:
```bash
pip uninstall crypto pycrypto
pip install pycryptodome
```
If user doesn't want to install anything: skip to manual JWT paste (pycryptodome is only needed for auto-auth).

**"Permission denied" reading Chrome Cookies**
→ Chrome is open and locking the file. The script copies it first, but on some systems this still fails.
Fix: tell the user to close Chrome completely, then re-run. Or use manual JWT paste.

**Windows / Linux users**
→ Chrome auto-auth does not work on Windows or Linux. Go straight to manual JWT paste. Do not waste time trying to make auto-auth work on these platforms.

**JWT seems to work but scrape returns 401 later**
→ JWT expired mid-session.
Fix: `python scraper.py auth --reset` then re-run the scrape from the beginning.

---

## STEP 3 — Discover available lists

**Run:**
```bash
python scraper.py discover
```

Read the full output. You'll get a list of API slugs like:
```
cybersecurity-seed
cybersecurity-series-a
enterprise-security-seed
...
```

Based on the user's intake answers, identify 1–3 slugs that best match. Rules:
- Prefer exact sector matches over broad ones
- Include both `seed` and `pre-seed` variants if the user wants early stage
- Do not pick more than 3 slugs — focused is better than comprehensive
- If no exact match exists, pick the closest and tell the user

**Show the user your slug selection and explain why before proceeding.** Example:
> "I'll pull from `cybersecurity-seed` and `cybersecurity-series-a`. The first covers seed-stage cyber investors, the second adds Series A. No pre-seed list exists for cybersecurity specifically. Confirm?"

Wait for confirmation. Do not scrape without it.

**Checkpoint:** User has confirmed the slug list.

---

### Discovery troubleshooting

**"No lists found" or 0 slugs returned**
→ Signal NFX changed their page HTML. The regex may have stopped matching.
Fix: run this to inspect the raw HTML:
```bash
python -c "
import urllib.request
req = urllib.request.Request('https://signal.nfx.com/investor-lists', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as r:
    html = r.read().decode()
# Look for investor-list hrefs
import re
print('\n'.join(re.findall(r'/investor-lists/[\w\-]+', html)[:20]))
"
```
If hrefs appear but with a different pattern, update the regex in `scraper.py`'s `cmd_discover` function.

**Slug the user mentions doesn't appear in discover output**
→ They may be using the URL slug format (e.g. `top-cybersecurity-seed-investors`) instead of the API format.
Fix: strip `top-` from the start and `-investors` from the end. `top-cybersecurity-seed-investors` → `cybersecurity-seed`.
Never pass URL-format slugs to the scrape command.

**A slug appears in discover but returns "not found" during scrape**
→ The list may have been removed or renamed by Signal NFX.
Fix: re-run `discover` to get a fresh list and pick an alternative slug.

---

## STEP 4 — Run the scrape

Build the command from the intake answers. Use these exact parameter formats:

**Location values that work:**
- USA → `"United States"`
- UK → `"United Kingdom"`
- Europe (broad) → `"Europe"`
- Multiple → `"United States,Canada"`
- Global investors → add `"Global"` to capture people who invest worldwide: `"United States,Global"`

**Check size in dollars (no commas, no $ sign):**
- Pre-seed → `--min-check 100000 --max-check 2000000`
- Seed → `--min-check 250000 --max-check 5000000`
- Series A → `--min-check 1000000 --max-check 20000000`
- If user said "doesn't matter" → omit both flags

**Output filename:** make it descriptive. `cybersecurity-usa-seed-investors.csv`

**Example command:**
```bash
python scraper.py scrape \
  --slugs "cybersecurity-seed,cybersecurity-series-a" \
  --locations "United States,Global" \
  --min-check 250000 \
  --max-check 5000000 \
  --output cybersecurity-usa-seed-investors.csv
```

Large lists (1000+ investors) take 1–2 minutes. Tell the user this if they seem to be waiting. The script handles pagination and rate limiting automatically — do not interrupt it.

**Checkpoint:** Script finishes and reports row counts.

---

### Scrape troubleshooting

**0 rows after location filter**
→ The location string didn't match any values in the data. This is the most common issue.
Fix: re-run without `--locations` to get the raw list, then check what location values actually appear:
```bash
python scraper.py scrape --slugs "cybersecurity-seed" --output cybersecurity-raw.csv
python -c "
import csv
locs = set()
for row in csv.DictReader(open('cybersecurity-raw.csv')):
    for l in row['investment_locations'].split(', '):
        locs.add(l.strip())
print(sorted(locs))
"
```
Use the exact strings that appear in the output as your `--locations` values.

**403 error during scrape**
→ Usually means the JWT expired or was rejected.
Fix: `python scraper.py auth --reset` then re-run.

**429 error / rate limited**
→ Script handles this automatically with exponential backoff. If it keeps happening after multiple retries, stop and wait 5 minutes before trying again.

**Scrape hangs on a large list**
→ Normal — large lists paginate through hundreds of pages. 1000 investors ≈ 10 pages ≈ ~30 seconds. Do not interrupt.

**"Slug not found" for a slug that appeared in discover**
→ Signal NFX occasionally restructures lists. Re-run discover to confirm it still exists.

**GraphQL error mentioning unknown field**
→ Signal NFX may have changed their schema. Do not add or guess field names.
Fields confirmed to work: `person.id`, `person.first_name`, `person.last_name`, `person.name`, `person.slug`, `person.linkedin_url`, `person.twitter_url`, `person.image_url`, `node.id`, `node.position`, `node.min_investment`, `node.max_investment`, `node.target_investment`, `node.stages`, `node.investment_locations`, `firm.id`, `firm.name`, `firm.slug`, `firm.description`, `firm.twitter_url`, `firm.linkedin_url`, `firm.url`, `firm.crunchbase_url`, `firm.angellist_url`.
Fields that do NOT exist (do not try them): `person.twitter`, `person.website`, `person.photo_url`, `person.location`, `firm.website_url`, `firm.website`, `node.investment_themes`, `node.investment_stages`, `node.sectors`, `node.tags`, `node.score`.

---

## STEP 5 — Validate and report

After the scrape completes, verify the output before telling the user it's done.

**Run:**
```bash
python -c "
import csv
rows = list(csv.DictReader(open('FILENAME.csv')))
print(f'Rows: {len(rows)}')
if rows:
    r = rows[0]
    print(f'Sample: {r[\"name\"]} @ {r[\"firm\"]} | LinkedIn: {r[\"linkedin_url\"]} | Locations: {r[\"investment_locations\"]}')
"
```

Replace `FILENAME.csv` with the actual output filename.

**Checkpoint:** File exists, row count > 0, sample row looks correct.

If row count is 0: do not tell the user it worked. Go back to scrape troubleshooting.

**Report to the user:**
> "Done — [N] investors saved to `[filename].csv`
> Columns: name, firm, LinkedIn URL, check size (min/max), stages, investment locations
> Next step: upload to Clay or Google Sheets. The `linkedin_url` column is ready for enrichment."

---

## Quick reference — common intent to slug mappings

| User says | Slugs to try |
|-----------|-------------|
| cybersecurity / security | `cybersecurity-seed`, `cybersecurity-series-a`, `enterprise-security-seed` |
| EdTech / education | `edtech-seed`, `education-seed`, `education-pre-seed`, `education-series-a` |
| climate / cleantech | `climate-tech-seed`, `cleantech-seed`, `sustainability-seed` |
| fintech | `fintech-seed`, `fintech-series-a` |
| impact / ESG | `impact-seed`, `social-impact-seed`, `impact-pre-seed` |
| B2B SaaS / enterprise | `enterprise-seed`, `saas-seed`, `b2b-seed` |
| future of work / HR tech | `future-of-work-seed`, `hr-tech-seed` |
| healthcare / health tech | `healthcare-seed`, `digital-health-seed` |
| consumer | `consumer-seed`, `consumer-series-a` |
| angel investors | `angel-scout-and-solo-capitalists` |

Always confirm these against `discover` output — Signal NFX adds and renames lists. This table is a starting point, not a definitive list.
