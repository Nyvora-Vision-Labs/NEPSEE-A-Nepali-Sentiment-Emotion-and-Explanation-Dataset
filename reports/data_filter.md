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

## 3. Final Output

Saved to `filtered_data.csv` with `index=False`.

| Stage | Tweet count | Removed |
|---|---|---|
| Raw scraped | 9,931 | — |
| After dropping English-only | 7,102 | 2,829 |
| After stripping English chars from mixed tweets | 7,102 | 0 (text cleaned, no rows dropped) |
| After dropping <4-word sentences | **6,824** | 278 |

**Final dataset: 6,824 Nepali-language tweets**, columns: `handle, id, text, created_at, likes, retweets, url, text_nepali_only, word_count`.

## Notes / Open Items

- `text_nepali_only` extraction is character-run based, not word-boundary aware — glued tokens (e.g. Nepali word + English suffix with no space) are split at the script boundary rather than dropped or kept whole.
- Devanagari danda (`।`) and double-danda (`॥`) punctuation are treated as separate runs (space-joined), which may affect downstream tokenization if sentence-final punctuation needs to stay attached to the preceding word.
- Word-count threshold (≥4) was applied to the *cleaned* Nepali-only text, not the original mixed-language tweet — a tweet with 6 mixed words but only 3 Nepali ones would be dropped even though it looked long enough pre-cleaning.