# post_quote.py
import os
import re
import random
import sys
from typing import Dict
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

def choose_quote(quotes: Dict[str,str], counts: Dict[str,int]) -> str:
    # ensure all quote ids have a count entry
    for qid in quotes:
        counts.setdefault(qid, 0)
    # find min count
    min_count = min(counts[qid] for qid in quotes)
    candidates = [qid for qid in quotes if counts[qid] == min_count]
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
    qid = choose_quote(quotes, counts)
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
    print("Counts updated.")

if __name__ == "__main__":
    main()
