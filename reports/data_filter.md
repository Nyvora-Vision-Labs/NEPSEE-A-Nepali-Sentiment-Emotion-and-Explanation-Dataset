# NEPSEE Dataset — Collection & Filtering Pipeline

## 1. Data Collection

Scraped tweets from 20 Nepali political and public figures (politicians, journalists, commentators) using **Twikit** (via the [PawiX25/twifork](https://github.com/PawiX25/twifork) maintained fork, needed after the upstream package broke under 2026 changes to X's internal API).

- **Authentication**: X's password-based login flow was no longer reachable programmatically, so authentication was done via cookies (`auth_token`, `ct0`, etc.) exported from a logged-in browser session, loaded via `client.set_cookies()`.
- **Target**: up to 500 tweets per account, paginated via the timeline cursor (`results.next()`), deduplicated by tweet ID.
- **Rate limiting**: X's undocumented throttling (~429 errors every couple of accounts) was handled with a 16-minute cooldown-and-retry loop, checkpointed to disk after every account so the run could resume if interrupted. The script was left running unattended overnight with a crash-safe outer loop that logged errors and auto-restarted.
- **Output**: `tweets.csv` with columns `handle, id, text, created_at, likes, retweets, url`.

**Total collected: 9,931 tweets**

## 2. Language Filtering

### Step 1 — Drop English-only tweets
Checked each tweet's `text` for the presence of any Devanagari character (Unicode range `\u0900`–`\u097F`). Tweets with **zero** Devanagari characters (pure English) were dropped; tweets with **any** Devanagari content (Nepali-only or mixed Nepali/English) were kept.

```python
def contains_nepali(text):
    if not isinstance(text, str) or not text.strip():
        return False
    return any(0x0900 <= ord(ch) <= 0x097F for ch in text)

df_filtered = df[df["text"].apply(contains_nepali)].reset_index(drop=True)
```

**Result: kept 7,102 of 9,931 tweets** (removed 2,829 pure-English tweets)
5803 of 7102 tweets contained both Nepali and English
4510 of 7102 tweets contained an http(s) link

### Step 2 — Strip English characters from mixed-language tweets
For tweets containing both Nepali and English, extracted only the contiguous Devanagari character runs, discarding English words, digits, punctuation, hashtags/mentions written in Latin script, and URLs.

```python
import re

DEVANAGARI_RUN = re.compile(r"[\u0900-\u097F]+")

def extract_nepali_only(text):
    if not isinstance(text, str):
        return ""
    runs = DEVANAGARI_RUN.findall(text)
    return " ".join(runs)

df_filtered["text_nepali_only"] = df_filtered["text"].apply(extract_nepali_only)
```

A validation pass (`is_nepali_only`, checking for any remaining Latin characters) confirmed no English text leaked through into `text_nepali_only`.

### Step 3 — Drop short sentences (<4 words)
Computed word count on the cleaned `text_nepali_only` column and dropped any tweet with fewer than 4 Nepali words, on the basis that very short fragments carry limited signal for sentiment/emotion labeling.

```python
df_filtered["word_count"] = df_filtered["text_nepali_only"].apply(
    lambda t: len(t.split()) if isinstance(t, str) else 0
)
df_filtered = df_filtered[df_filtered["word_count"] >= 4].reset_index(drop=True)
```

**Result: kept 6,824 of 7,102 tweets** (removed 278 short fragments)

## 3. Tweet-Level Output

Saved to `filtered_data.csv` with `index=False`.

| Stage | Tweet count | Removed |
|---|---|---|
| Raw scraped | 9,931 | — |
| After dropping English-only | 7,102 | 2,829 |
| After stripping English chars from mixed tweets | 7,102 | 0 (text cleaned, no rows dropped) |
| After dropping <4-word sentences | **6,824** | 278 |

**Tweet-level dataset: 6,824 Nepali-language tweets**, columns: `handle, id, text, created_at, likes, retweets, url, text_nepali_only, word_count`.

## 4. Sentence Splitting

The tweet-level corpus above was expanded so that **each row is a single sentence**, because a tweet can shift sentiment between its own clauses and a single per-tweet label would flatten that.

Splitting is done in `split_sentences.py` on the cleaned `text_nepali_only` column, breaking on the Devanagari danda (`।`) followed by whitespace, or on newlines:

```python
parts = re.split(r"(?<=।)\s+|\n+", text)
```

Each output row keeps every original tweet column and gains three new ones: `tweet_id` (pointing back to the source tweet), `sentence_text`, and `sentence_index` (0-based position within the tweet). A positional `row_id` is prepended. Any pre-existing `sentiment` value is inherited only by the first sub-row; later sub-rows start blank so every sentence gets labelled on its own.

**Result: 6,824 tweets → 12,282 sentence rows** (5,458 new rows), mean 1.80 sentences per tweet.

| Sentences produced | Tweets |
|---|---|
| 1 | 3,751 |
| 2 | 1,602 |
| 3 | 882 |
| 4 | 380 |
| 5 | 130 |
| 6 | 53 |
| 7 | 19 |
| 8 | 3 |
| 9 | 4 |

So 3,073 of 6,824 tweets (45%) carried more than one sentence.

The script is idempotent — it detects the `row_id` / `tweet_id` columns and refuses to re-expand an already-split file. Note that it copies `filtered_data.csv` to `filtered_data_backup.csv` *before* that check, so re-running it overwrites the pre-split backup even though it does nothing else.

## 5. Drop Short Sentences (<5 words)

The tweet-level `≥4` word threshold from Step 3 was applied to whole tweets, so splitting re-introduced short fragments: a 20-word tweet passing the filter could still break into a 15-word clause and a 3-word one. A second pass, `drop_short_sentences.py`, applies a `MIN_WORDS = 5` threshold to `sentence_text` directly.

```python
words = df["sentence_text"].fillna("").str.split().map(len)
kept = df[words >= MIN_WORDS]
```

**Result: kept 10,947 of 12,282 sentence rows** (removed 1,335 fragments).

| Sentence length | Rows dropped |
|---|---|
| 1 word | 182 |
| 2 words | 274 |
| 3 words | 324 |
| 4 words | 555 |
| **Total** | **1,335** |

Typical discards: `जय नेपाल`, `राधे`, `शंकर लामिछाने`, `भिडियोमा पनि ।`, `हामी जनादेश मान्ने।` — greetings, names, and sentence fragments that carry no independently labellable sentiment.

Dropping these eliminated 163 tweets entirely (every one of their sentences was too short), taking source-tweet coverage from 6,824 to 6,661. Mean sentence length rose from 13.1 to 14.3 words, median from 11 to 12.

`row_id` was deliberately **not** renumbered — the gaps are harmless because the annotation app keys labels on `tweet_id:sentence_index`, not on row position, so no existing annotation was orphaned by the removal. `row_id` only travels through to the export.

## 6. Final Output

| Stage | Rows | Unit | Removed |
|---|---|---|---|
| Raw scraped | 9,931 | tweets | — |
| After dropping English-only | 7,102 | tweets | 2,829 |
| After stripping English chars | 7,102 | tweets | 0 |
| After dropping <4-word tweets | 6,824 | tweets | 278 |
| After sentence splitting | 12,282 | sentences | +5,458 |
| After dropping <5-word sentences | **10,947** | sentences | 1,335 |

**Annotation corpus: 10,947 Nepali sentences drawn from 6,661 tweets**, columns: `row_id, handle, id, text, created_at, likes, retweets, url, text_nepali_only, is_valid_nepali_only, word_count, sentiment, tweet_id, sentence_text, sentence_index`.

Pipeline order for future scrapes: `scrape.py` → language filtering (`analyze.ipynb`) → `split_sentences.py` → `drop_short_sentences.py`.

## Notes / Open Items

- `text_nepali_only` extraction is character-run based, not word-boundary aware — glued tokens (e.g. Nepali word + English suffix with no space) are split at the script boundary rather than dropped or kept whole.
- Devanagari danda (`।`) and double-danda (`॥`) punctuation are treated as separate runs (space-joined), which may affect downstream tokenization if sentence-final punctuation needs to stay attached to the preceding word.
- Word-count threshold (≥4) was applied to the *cleaned* Nepali-only text, not the original mixed-language tweet — a tweet with 6 mixed words but only 3 Nepali ones would be dropped even though it looked long enough pre-cleaning.
- The word-count threshold is applied twice at different granularities — `≥4` on whole tweets (Step 3) and `≥5` on individual sentences (Step 5). The tweet-level pass is now largely redundant; a future re-run could skip it and filter only after splitting.
- Sentence splitting is punctuation-driven, so a tweet written without any danda or line break stays a single row no matter how many clauses it contains, and a danda used as an abbreviation mark would split mid-sentence.
- Corpus size is now 10,947 sentences; more scraping is planned to grow it rather than relaxing the `MIN_WORDS = 5` threshold.
