"""
scrape.py
---------
Sample scraper: fetches ONE recent tweet from each account in accounts.json
and stores the results in a CSV file.

Uses twscrape (the actively maintained option, since snscrape is broken on
current Python/X). Login credentials are read from a local .env file that
is NOT committed to git (see .gitignore).

=========================================================================
ONE-TIME SETUP
=========================================================================

1. Install dependencies:
       pip install twscrape python-dotenv

2. Copy the template and fill in a SPARE X account (not your main one):
       cp .env.example .env
       # then edit .env with real values

3. Just run the script — it will automatically add the account to
   twscrape's local pool and log in if it hasn't already:
       python scrape.py

   The first run may prompt for a captcha/email verification code in
   the terminal depending on the account — follow the prompts.

Files created automatically (already in .gitignore, do not commit):
   - accounts.db     -> twscrape's local session/login database
   - .env            -> your real credentials
   - accounts_sample.csv -> scraped output
=========================================================================
"""

import asyncio
import csv
import json
import os
import time

from dotenv import load_dotenv
from twscrape import API

# -----------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_JSON = os.path.join(BASE_DIR, "accounts.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")
OUTPUT_CSV = "accounts_sample.csv"
DELAY_BETWEEN_REQUESTS_SEC = 3  # be gentle to avoid rate limits / flags

load_dotenv(ENV_FILE)

TWITTER_USERNAME = os.environ.get("TWITTER_USERNAME")
TWITTER_PASSWORD = os.environ.get("TWITTER_PASSWORD")
TWITTER_EMAIL = os.environ.get("TWITTER_EMAIL")
TWITTER_EMAIL_PASSWORD = os.environ.get("TWITTER_EMAIL_PASSWORD")


def load_target_accounts(path: str = ACCOUNTS_JSON):
    with open(path, "r", encoding="utf-8") as f:
        accounts = json.load(f)

    required_keys = {"Name", "Handle", "Role"}
    for i, acc in enumerate(accounts):
        missing = required_keys - acc.keys()
        if missing:
            raise ValueError(f"accounts.json entry {i} is missing keys: {missing}")
    return accounts


async def ensure_logged_in(api: API):
    """Add the scraping account from .env to twscrape's pool (if not
    already added) and make sure it's logged in."""
    missing_env = [
        name for name, val in [
            ("TWITTER_USERNAME", TWITTER_USERNAME),
            ("TWITTER_PASSWORD", TWITTER_PASSWORD),
            ("TWITTER_EMAIL", TWITTER_EMAIL),
            ("TWITTER_EMAIL_PASSWORD", TWITTER_EMAIL_PASSWORD),
        ] if not val
    ]
    if missing_env:
        raise RuntimeError(
            f"Missing values in .env: {', '.join(missing_env)}. "
            f"Copy .env.example to .env and fill it in."
        )

    existing = await api.pool.accounts_info()
    already_added = any(a["username"] == TWITTER_USERNAME for a in existing)

    if not already_added:
        print(f"Adding account @{TWITTER_USERNAME} to twscrape pool...")
        await api.pool.add_account(
            TWITTER_USERNAME, TWITTER_PASSWORD, TWITTER_EMAIL, TWITTER_EMAIL_PASSWORD
        )

    print("Logging in (may prompt for captcha/email code)...")
    await api.pool.login_all()


async def fetch_one_tweet(api: API, handle: str):
    """Return (tweet_id, text, date, url) for the most recent tweet, or None."""
    try:
        user = await api.user_by_login(handle)
        if user is None:
            print(f"  [twscrape] user not found: @{handle}")
            return None

        tweets = await api.user_tweets(user.id, limit=5)
        async for tweet in tweets:
            url = f"https://twitter.com/{handle}/status/{tweet.id}"
            return tweet.id, tweet.rawContent, tweet.date.isoformat(), url

        print(f"  [twscrape] no tweets found: @{handle}")
        return None

    except Exception as e:
        print(f"  [twscrape error] @{handle}: {e}")
        return None


async def main_async():
    target_accounts = load_target_accounts()
    print(f"Loaded {len(target_accounts)} target accounts from {ACCOUNTS_JSON}\n")

    api = API()  # stores/reads session data in accounts.db (gitignored)
    await ensure_logged_in(api)
    print()

    rows = []
    for account in target_accounts:
        handle = account["Handle"]
        print(f"Fetching @{handle} ({account['Name']}) ...")

        result = await fetch_one_tweet(api, handle)

        if result:
            tweet_id, text, date, url = result
            rows.append({
                "name": account["Name"],
                "handle": handle,
                "role": account["Role"],
                "tweet_id": tweet_id,
                "tweet_text": text,
                "tweet_date": date,
                "tweet_url": url,
            })
        else:
            rows.append({
                "name": account["Name"],
                "handle": handle,
                "role": account["Role"],
                "tweet_id": "",
                "tweet_text": "",
                "tweet_date": "",
                "tweet_url": "",
            })

        time.sleep(DELAY_BETWEEN_REQUESTS_SEC)

    fieldnames = ["name", "handle", "role", "tweet_id", "tweet_text", "tweet_date", "tweet_url"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. Wrote {len(rows)} rows to {OUTPUT_CSV}")
    missing = [r["handle"] for r in rows if not r["tweet_id"]]
    if missing:
        print(f"Could not fetch tweets for: {', '.join(missing)}")
        print("Common causes: handle changed/suspended, login not fully "
              "completed (captcha pending), or rate limiting.")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()