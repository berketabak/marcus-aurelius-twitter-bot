# post_quote.py
import os
import re
import random
import sys
from datetime import datetime
from typing import Dict, List, Set
from zoneinfo import ZoneInfo
import tweepy

from dotenv import load_dotenv
load_dotenv()


# Env vars (GitHub Actions'ta secrets olarak eklenecek)
API_KEY = os.getenv("TWITTER_API_KEY")
API_KEY_SECRET = os.getenv("TWITTER_API_KEY_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

QUOTES_FILE = "quotes.txt"
COUNTS_FILE = "counts.txt"
HISTORY_FILE = "posted_quotes.txt"
HISTORY_LIMIT = 10

def read_quotes(path: str) -> Dict[str,str]:
    quotes = {}
    pattern = re.compile(r'^\s*(\d+)-\s*(.+)$')
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                quotes[m.group(1)] = m.group(2).strip()
    return quotes

def read_counts(path: str) -> Dict[str,int]:
    counts = {}
    if not os.path.exists(path):
        return counts
    pattern = re.compile(r'^\s*(\d+)-\s*(\d+)\s*$')
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                counts[m.group(1)] = int(m.group(2))
    return counts

def write_counts(path: str, counts: Dict[str,int]):
    # sort by numeric id
    items = sorted(counts.items(), key=lambda kv: int(kv[0]))
    with open(path, "w", encoding="utf-8") as f:
        for k,v in items:
            f.write(f"{k}-{v}\n")

def read_recent_quote_ids(path: str, limit: int) -> Set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        entries: List[str] = [line.strip() for line in f if line.strip()]
    quote_ids = []
    for entry in entries:
        match = re.search(r"(?:Alıntı #(\d+)|quote_id=(\d+))", entry)
        if match:
            quote_ids.append(match.group(1) or match.group(2))
        else:
            # Backward compatibility with the original qid<TAB>quote format.
            legacy_id = re.match(r"(\d+)\t", entry)
            if legacy_id:
                quote_ids.append(legacy_id.group(1))
    return set(quote_ids[-limit:])

def history_entry_count(path: str) -> int:
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())

def append_to_history(path: str, post_number: int, qid: str, quote_text: str):
    posted_at = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(
            f"Paylaşım #{post_number} | Alıntı #{qid} | "
            f"Paylaşım zamanı: {posted_at} (TR) | {quote_text}\n"
        )

def choose_quote(quotes: Dict[str,str], counts: Dict[str,int], excluded_ids: Set[str]) -> str:
    # ensure all quote ids have a count entry
    for qid in quotes:
        counts.setdefault(qid, 0)
    eligible_ids = [qid for qid in quotes if qid not in excluded_ids]
    # If there are fewer quotes than the history window, allow repeats.
    if not eligible_ids:
        eligible_ids = list(quotes)
    min_count = min(counts[qid] for qid in eligible_ids)
    candidates = [qid for qid in eligible_ids if counts[qid] == min_count]
    chosen = random.choice(candidates)
    return chosen

def post_to_twitter(text: str):
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_KEY_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )
    # Optional: trim or validate length < 280. Here we post as single tweet.
    resp = client.create_tweet(text=text)
    return resp

def main():
    if not (API_KEY and API_KEY_SECRET and ACCESS_TOKEN and ACCESS_TOKEN_SECRET):
        print("Missing Twitter API credentials in environment.", file=sys.stderr)
        sys.exit(1)

    quotes = read_quotes(QUOTES_FILE)
    if not quotes:
        print("No quotes found.", file=sys.stderr)
        sys.exit(1)

    counts = read_counts(COUNTS_FILE)
    recent_quote_ids = read_recent_quote_ids(HISTORY_FILE, HISTORY_LIMIT)
    qid = choose_quote(quotes, counts, recent_quote_ids)
    post_number = history_entry_count(HISTORY_FILE) + 1
    quote_text = quotes[qid]
    # tweet_text = f"{quote_text}\n\n— Marcus Aurelius"   # sondaki Marcus Aurelius imzasını kaldırdık
    tweet_text = quote_text


    print(f"Selected [{qid}]: {quote_text}")

    try:
        resp = post_to_twitter(tweet_text)
        print("Tweet posted, id:", getattr(resp, "data", None))
    except Exception as e:
        print("Failed to post tweet:", e, file=sys.stderr)
        sys.exit(1)

    # only update counts after successful post
    counts[qid] = counts.get(qid, 0) + 1
    write_counts(COUNTS_FILE, counts)
    append_to_history(HISTORY_FILE, post_number, qid, quote_text)
    print("Counts and local post history updated.")

if __name__ == "__main__":
    main()
