"""
Scrape recent tweets for a list of X/Twitter accounts using Twikit.

Setup:
    pip install twikit
    # If the upstream package breaks (common in 2026 due to X's internal API
    # changes), use the maintained fork instead:
    # pip install git+https://github.com/PawiX25/twifork

Usage:
    1. Put accounts.json (list of {"Name", "Handle", "Role"}) next to this script,
       or pass a path with --input.
    2. X's password-based LoginFlow is no longer reachable from a script
       (as of 2026 it requires a browser-generated token). Instead:
         a. Log into x.com in a normal browser with your account.
         b. Use a cookie-export extension (e.g. Cookie-Editor) to export
            the x.com cookies, at minimum "auth_token" and "ct0".
         c. Save the raw export as cookies.json next to this script —
            either a flat {"auth_token": "...", "ct0": "..."} dict, or
            Cookie-Editor's [{"name": ..., "value": ...}, ...] array
            format both work; the script normalizes it automatically.
    3. Run: python scrape_tweets.py

Output:
    tweets.json  -> {handle: [ {id, text, created_at, likes, retweets, url}, ... ]}
    tweets.csv   -> flat table, one row per tweet
"""

import asyncio
import csv
import json
import logging
import sys
import traceback
from pathlib import Path

from twikit import Client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    handlers=[logging.FileHandler("scrape.log", encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("scrape")

# ---- CONFIG ---------------------------------------------------------------
INPUT_FILE = "accounts.json"
OUTPUT_JSON = "tweets.json"
OUTPUT_CSV = "tweets.csv"
TWEETS_PER_ACCOUNT = 500        # how many recent tweets to pull per account
DELAY_BETWEEN_ACCOUNTS = 8      # seconds, be gentle to avoid throttling/bans
PAGE_DELAY = 3                  # seconds between paginated requests within an account
RATE_LIMIT_COOLDOWN = 16 * 60   # seconds to wait after a 429 before retrying (X's window is ~15 min)
MAX_RATE_LIMIT_RETRIES = 1000   # effectively unlimited — keep retrying overnight rather than give up
CRASH_COOLDOWN = 5 * 60         # seconds to wait before restarting after an unexpected crash
LOG_FILE = "scrape.log"         # progress log, readable while the console isn't watched
#COOKIES_FILE = "cookies.json"   # exported from a real browser session, see docstring above
# -----------------------------------------------------------------------


def load_handles(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    accounts = []
    for entry in data:
        handle = entry.get("Handle", "").lstrip("@").strip()
        if handle:
            accounts.append({"name": entry.get("Name", ""), "handle": handle})
    return accounts


def normalize_cookies(raw) -> dict:
    """
    Accepts either:
      - a flat dict:  {"auth_token": "...", "ct0": "...", ...}
      - a Cookie-Editor style export: [{"name": ..., "value": ...}, ...]
    and returns a flat {name: value} dict, which is what twikit needs.
    """
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        return {c["name"]: c["value"] for c in raw if "name" in c and "value" in c}
    raise ValueError("Unrecognized cookies.json format")


async def get_client() -> Client:
    """
    X's LoginFlow is no longer reachable from a plain HTTP client (it now
    requires a browser-generated $castle_token). login() with username/
    password/email is broken as of 2026. Instead, cookies exported from a
    real logged-in browser session are loaded here.
    """
    client = Client("en-US")
    cookies_path = Path(COOKIES_FILE)
    if not cookies_path.exists():
        raise SystemExit(
            f"{COOKIES_FILE} not found. Export cookies (auth_token, ct0, etc.) "
            "from a browser session logged into x.com and save them as "
            f"{COOKIES_FILE} — see comments at the top of this file."
        )
    raw = json.loads(cookies_path.read_text(encoding="utf-8"))
    cookie_dict = normalize_cookies(raw)
    client.set_cookies(cookie_dict)
    return client


async def scrape_account(client: Client, handle: str, count: int) -> list[dict]:
    try:
        user = await client.get_user_by_screen_name(handle)
    except Exception as e:
        log.info(f"  [!] Could not resolve @{handle}: {e}")
        return []

    tweets = []
    seen_ids = set()
    results = None
    try:
        results = await user.get_tweets("Tweets", count=20)
    except Exception as e:
        if "429" in str(e):
            log.info(f"  [!] Rate limited immediately on @{handle}, will retry later")
            raise RateLimited(handle) from e
        log.info(f"  [!] Error fetching tweets for @{handle}: {e}")
        return []

    while results and len(tweets) < count:
        for t in results:
            if t.id in seen_ids:
                continue
            seen_ids.add(t.id)
            tweets.append(
                {
                    "id": t.id,
                    "text": t.text,
                    "created_at": t.created_at,
                    "likes": getattr(t, "favorite_count", None),
                    "retweets": getattr(t, "retweet_count", None),
                    "url": f"https://x.com/{handle}/status/{t.id}",
                }
            )
            if len(tweets) >= count:
                break
        if len(tweets) >= count:
            break
        await asyncio.sleep(PAGE_DELAY)
        try:
            results = await results.next()
        except Exception as e:
            if "429" in str(e):
                # Partial progress is still useful — return what we have,
                # caller decides whether to retry this handle later.
                log.info(f"  [!] Rate limited mid-account on @{handle} after {len(tweets)} tweets")
                raise RateLimited(handle, partial=tweets) from e
            log.info(f"  [!] Pagination stopped for @{handle}: {e}")
            break
        if not results:
            break

    return tweets


class RateLimited(Exception):
    """Raised when X returns 429. May carry partial results already fetched."""

    def __init__(self, handle: str, partial: list[dict] | None = None):
        super().__init__(handle)
        self.handle = handle
        self.partial = partial or []


async def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else INPUT_FILE
    if not Path(input_path).exists():
        log.info(f"Input file not found: {input_path}")
        log.info("Place accounts.json next to this script, or pass a path:")
        log.info("  python scrape_tweets.py /path/to/accounts.json")
        return

    accounts = load_handles(input_path)
    log.info(f"Loaded {len(accounts)} accounts from {input_path}")

    client = await get_client()

    # Resume support: load whatever was already saved from a prior run.
    all_tweets: dict[str, list[dict]] = {}
    out_path = Path(OUTPUT_JSON)
    if out_path.exists():
        all_tweets = json.loads(out_path.read_text(encoding="utf-8"))
        log.info(f"Resuming — {len(all_tweets)} accounts already have saved data")

    def save_progress():
        out_path.write_text(
            json.dumps(all_tweets, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["handle", "id", "text", "created_at", "likes", "retweets", "url"])
            for h, tw in all_tweets.items():
                for t in tw:
                    writer.writerow(
                        [h, t["id"], t["text"], t["created_at"], t["likes"], t["retweets"], t["url"]]
                    )

    for acc in accounts:
        handle = acc["handle"]
        existing = all_tweets.get(handle, [])
        if len(existing) >= TWEETS_PER_ACCOUNT:
            log.info(f"Skipping @{handle}, already have {len(existing)} tweets")
            continue

        log.info(f"Scraping @{handle} ({acc['name']})...")
        attempt = 0
        while True:
            attempt += 1
            try:
                tweets = await scrape_account(client, handle, TWEETS_PER_ACCOUNT)
                all_tweets[handle] = tweets
                log.info(f"  -> got {len(tweets)} tweets")
                break
            except RateLimited as rl:
                if rl.partial:
                    all_tweets[handle] = rl.partial  # keep partial progress
                    save_progress()
                if attempt >= MAX_RATE_LIMIT_RETRIES:
                    log.info(f"  [!] Giving up on @{handle} after {attempt} rate-limit retries")
                    all_tweets.setdefault(handle, rl.partial)
                    break
                log.info(f"  [!] Rate limited — waiting {RATE_LIMIT_COOLDOWN}s before retrying @{handle}")
                await asyncio.sleep(RATE_LIMIT_COOLDOWN)

        save_progress()
        await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    log.info(f"\nSaved {OUTPUT_JSON} and {OUTPUT_CSV}")


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
            log.info("All accounts complete — exiting.")
            break
        except KeyboardInterrupt:
            log.info("Stopped by user (Ctrl+C).")
            break
        except SystemExit:
            raise
        except Exception:
            log.error("Unexpected crash, will restart after cooldown:\n%s", traceback.format_exc())
            import time
            time.sleep(CRASH_COOLDOWN)
            log.info("Restarting run...")