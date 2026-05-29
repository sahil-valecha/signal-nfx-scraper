"""
Signal NFX Investor Scraper

Usage:
  python scraper.py discover                          # List all available investor lists
  python scraper.py scrape --slugs "cybersecurity-seed,cybersecurity-series-a"
  python scraper.py scrape --slugs "cybersecurity-seed" --locations "United States" --min-check 500000
  python scraper.py filter --input raw.csv --locations "United States" --min-check 500000

The Claude Code skill (.claude/commands/signal-nfx.md) drives this automatically.
You don't need to run these commands directly.
"""

import argparse
import csv
import json
import time
import sys
import re
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from auth import get_jwt, clear_jwt

API_URL = "https://signal-api.nfx.com/graphql"
LISTS_URL = "https://signal.nfx.com/investor-lists"

GRAPHQL_QUERY = """
query vclInvestors($slug: String!, $after: String) {
  list(slug: $slug) {
    id slug investor_count
    scored_investors(first: 100, after: $after) {
      pageInfo { hasNextPage endCursor }
      edges {
        node {
          id
          person {
            id first_name last_name name slug
            linkedin_url twitter_url image_url
          }
          position
          min_investment max_investment target_investment
          stages { id display_name }
          investment_locations { id display_name }
          firm {
            id name slug description
            twitter_url linkedin_url url crunchbase_url angellist_url
          }
        }
      }
    }
  }
}
"""


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _make_request(url: str, payload: dict | None = None, jwt: str | None = None, retries: int = 3) -> dict:
    """Make a GET or POST request. Uses urllib to avoid Cloudflare blocks."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/html, */*",
    }
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"
        headers["Origin"] = "https://signal.nfx.com"
        headers["Referer"] = "https://signal.nfx.com/"
        headers["Content-Type"] = "application/json"

    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise RuntimeError(
                    "Auth error (401/403). Your JWT may have expired.\n"
                    "Run: python scraper.py auth --reset\nThen try again."
                )
            if e.code == 429:
                wait = 10 * (2 ** attempt)
                print(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(5)
                continue
            raise

    raise RuntimeError("Max retries exceeded")


# ---------------------------------------------------------------------------
# Discover
# ---------------------------------------------------------------------------

def cmd_discover(args):
    """Fetch all available investor list slugs from Signal NFX."""
    print("Fetching available investor lists from Signal NFX...")
    try:
        req = urllib.request.Request(
            LISTS_URL,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode()
    except Exception as e:
        print(f"Error fetching lists page: {e}")
        sys.exit(1)

    # Extract all /investor-lists/<slug> hrefs
    raw_slugs = re.findall(r'/investor-lists/([\w\-]+)', html)
    # Convert URL slug format to API slug format: strip "top-" prefix and "-investors" suffix
    api_slugs = []
    seen = set()
    for s in raw_slugs:
        api = re.sub(r'^top-', '', s)
        api = re.sub(r'-investors$', '', api)
        if api not in seen and len(api) > 2:
            seen.add(api)
            api_slugs.append((s, api))

    if not api_slugs:
        print("No lists found. Signal NFX may have changed their page structure.")
        sys.exit(1)

    print(f"\nFound {len(api_slugs)} investor lists:\n")
    for url_slug, api_slug in sorted(api_slugs, key=lambda x: x[1]):
        print(f"  {api_slug:<45}  (URL: /investor-lists/{url_slug})")

    print(f"\nTotal: {len(api_slugs)} lists")
    print("\nTo scrape one or more, run:")
    print('  python scraper.py scrape --slugs "<slug1>,<slug2>"')


# ---------------------------------------------------------------------------
# Scrape
# ---------------------------------------------------------------------------

def _scrape_list(slug: str, jwt: str) -> list[dict]:
    """Scrape all investors from a single list slug."""
    investors = []
    after = None
    page = 0

    # Verify slug exists
    verify = _make_request(API_URL, {
        "query": "query { list(slug: $slug) { id slug investor_count } }".replace(
            "$slug", f'"{slug}"'
        ).replace("$slug", f'"{slug}"'),
        "variables": {"slug": slug}
    }, jwt=jwt)

    lst = verify.get("data", {}).get("list")
    if not lst:
        print(f"  Slug '{slug}' not found on Signal NFX. Skipping.")
        return []

    total = lst.get("investor_count", "?")
    print(f"  Scraping '{slug}' ({total} investors)...")

    while True:
        payload = {
            "query": GRAPHQL_QUERY,
            "variables": {"slug": slug, "after": after}
        }
        result = _make_request(API_URL, payload, jwt=jwt)

        data = result.get("data", {}).get("list", {}).get("scored_investors", {})
        edges = data.get("edges", [])
        page_info = data.get("pageInfo", {})

        for edge in edges:
            node = edge.get("node", {})
            person = node.get("person") or {}
            firm = node.get("firm") or {}

            stages = " | ".join(s["display_name"] for s in (node.get("stages") or []))
            locations = ", ".join(l["display_name"] for l in (node.get("investment_locations") or []))
            firm_desc = (firm.get("description") or "").replace("\n", " ").strip()[:500]
            person_slug = person.get("slug", "")

            investors.append({
                "name": person.get("name", ""),
                "first_name": person.get("first_name", ""),
                "last_name": person.get("last_name", ""),
                "signal_profile_url": f"https://signal.nfx.com/investors/{person_slug}" if person_slug else "",
                "linkedin_url": person.get("linkedin_url", ""),
                "twitter_url": person.get("twitter_url", ""),
                "firm": firm.get("name", ""),
                "firm_slug": firm.get("slug", ""),
                "firm_description": firm_desc,
                "firm_twitter_url": firm.get("twitter_url", ""),
                "firm_linkedin_url": firm.get("linkedin_url", ""),
                "firm_url": firm.get("url", ""),
                "firm_crunchbase_url": firm.get("crunchbase_url", ""),
                "position": node.get("position", ""),
                "stages": stages,
                "min_investment": node.get("min_investment", ""),
                "max_investment": node.get("max_investment", ""),
                "target_investment": node.get("target_investment", ""),
                "investment_locations": locations,
                "source_list": slug,
            })

        page += 1
        if page % 5 == 0:
            time.sleep(1)

        if not page_info.get("hasNextPage"):
            break
        after = page_info.get("endCursor")

    print(f"  Done - {len(investors)} investors from '{slug}'")
    return investors


def cmd_scrape(args):
    jwt = get_jwt()
    slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]

    all_investors = []
    for i, slug in enumerate(slugs):
        if i > 0:
            time.sleep(5)
        investors = _scrape_list(slug, jwt)
        all_investors.extend(investors)

    print(f"\nTotal raw rows: {len(all_investors)}")

    # Dedup by signal_profile_url
    seen = {}
    deduped = []
    for inv in all_investors:
        key = inv["signal_profile_url"] or inv["name"] + inv["firm"]
        if key not in seen:
            seen[key] = inv
            deduped.append(inv)
        else:
            # Merge source lists
            existing = seen[key]
            existing_lists = set(existing["source_list"].split(","))
            existing_lists.add(inv["source_list"])
            existing["source_list"] = ",".join(sorted(existing_lists))

    print(f"After dedup: {len(deduped)} investors")

    # Apply filters
    filtered = _apply_filters(deduped, args)
    print(f"After filters: {len(filtered)} investors")

    # Write CSV
    output = args.output or _default_output_name(slugs, args)
    _write_csv(filtered, output)
    print(f"\nSaved to: {output}")


# ---------------------------------------------------------------------------
# Filter (post-process an existing CSV)
# ---------------------------------------------------------------------------

def cmd_filter(args):
    if not args.input:
        print("Error: --input <csv file> is required for the filter command.")
        sys.exit(1)

    with open(args.input, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} rows from {args.input}")
    filtered = _apply_filters(rows, args)
    print(f"After filters: {len(filtered)} rows")

    output = args.output or args.input.replace(".csv", "-filtered.csv")
    _write_csv(filtered, output)
    print(f"Saved to: {output}")


# ---------------------------------------------------------------------------
# Auth management
# ---------------------------------------------------------------------------

def cmd_auth(args):
    if args.reset:
        clear_jwt()
    jwt = get_jwt(force_manual=args.reset)
    print(f"JWT active (first 40 chars): {jwt[:40]}...")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _apply_filters(rows: list[dict], args) -> list[dict]:
    result = rows

    # Location filter
    if getattr(args, "locations", None):
        location_terms = [l.strip().lower() for l in args.locations.split(",")]
        result = [
            r for r in result
            if any(term in r.get("investment_locations", "").lower() for term in location_terms)
            or any(term in ["global", "worldwide"] for term in (r.get("investment_locations", "").lower().split(", ")))
        ]

    # Min check size filter
    if getattr(args, "min_check", None):
        def passes_min(r):
            try:
                max_inv = int(r.get("max_investment") or 0)
                return max_inv == 0 or max_inv >= args.min_check
            except (ValueError, TypeError):
                return True
        result = [r for r in result if passes_min(r)]

    # Max check size filter
    if getattr(args, "max_check", None):
        def passes_max(r):
            try:
                min_inv = int(r.get("min_investment") or 0)
                return min_inv == 0 or min_inv <= args.max_check
            except (ValueError, TypeError):
                return True
        result = [r for r in result if passes_max(r)]

    return result


def _default_output_name(slugs: list[str], args) -> str:
    base = slugs[0] if len(slugs) == 1 else f"{len(slugs)}-lists"
    loc = ""
    if getattr(args, "locations", None):
        loc = "-" + args.locations.split(",")[0].strip().lower().replace(" ", "-")
    return f"{base}{loc}-investors.csv"


def _write_csv(rows: list[dict], output: str):
    if not rows:
        print("No rows to write.")
        return
    fieldnames = list(rows[0].keys())
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Signal NFX Investor Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # discover
    subparsers.add_parser("discover", help="List all available Signal NFX investor lists")

    # scrape
    scrape_p = subparsers.add_parser("scrape", help="Scrape one or more investor lists")
    scrape_p.add_argument("--slugs", required=True, help="Comma-separated list slugs, e.g. 'cybersecurity-seed,cybersecurity-series-a'")
    scrape_p.add_argument("--locations", help="Filter by location, e.g. 'United States' or 'United States,Canada'")
    scrape_p.add_argument("--min-check", type=int, help="Minimum check size in dollars, e.g. 500000")
    scrape_p.add_argument("--max-check", type=int, help="Maximum check size in dollars, e.g. 10000000")
    scrape_p.add_argument("--output", help="Output CSV filename (auto-generated if not set)")

    # filter
    filter_p = subparsers.add_parser("filter", help="Filter an existing CSV by location or check size")
    filter_p.add_argument("--input", required=True, help="Input CSV file")
    filter_p.add_argument("--locations", help="Filter by location")
    filter_p.add_argument("--min-check", type=int, help="Minimum check size")
    filter_p.add_argument("--max-check", type=int, help="Maximum check size")
    filter_p.add_argument("--output", help="Output CSV filename")

    # auth
    auth_p = subparsers.add_parser("auth", help="Manage Signal NFX authentication")
    auth_p.add_argument("--reset", action="store_true", help="Clear cached JWT and re-authenticate")

    args = parser.parse_args()

    commands = {
        "discover": cmd_discover,
        "scrape": cmd_scrape,
        "filter": cmd_filter,
        "auth": cmd_auth,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
