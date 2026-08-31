# NEPSEE — A Nepali Sentiment, Emotion and Explanation Dataset

A corpus of Nepali-language tweets from public figures in politics, journalism and
civil society, split into individual sentences and annotated for sentiment by three
independent annotators.

**Status:** collection, filtering and sentence segmentation are complete. Sentiment
annotation is in progress via the web app in this repository. The *emotion* and
*explanation* layers named in the project title are planned but not yet built.

---

## Dataset at a glance

| | |
|---|---|
| Source accounts | 20 (9 politicians, 9 journalists, 2 activists) |
| Raw tweets scraped | 9,931 |
| Nepali tweets after filtering | 6,824 |
| Sentence rows for annotation | **12,282** |
| Nepali word tokens | ~160,600 |
| Date range | Dec 2017 – Aug 2026 |
| Sentences per tweet | 1.80 average, 9 maximum; 45% of tweets split into more than one |
| Words per sentence | 13.1 mean, 11 median |
| Annotators | 3, each labelling all 12,282 sentences independently |
| Label set | 5-point sentiment scale + `dont_know` |

---

## Pipeline

### 1. Collection — `scrape.py`

Tweets were pulled from 20 accounts using [Twikit](https://github.com/d60/twikit), via
the [PawiX25/twifork](https://github.com/PawiX25/twifork) fork, which is needed because
the upstream package broke against X's internal API changes in 2026.

X's password login flow is no longer reachable from a script — it now requires a
browser-generated token — so authentication uses cookies (`auth_token`, `ct0`) exported
from a logged-in browser session and saved as `cookies.json`. The script accepts either
a flat `{"name": "value"}` dict or a Cookie-Editor style array.

The scraper targets up to 500 tweets per account, paginating through the timeline cursor
and deduplicating by tweet ID. X throttles aggressively, so a 429 triggers a 16-minute
cooldown and retry, with progress checkpointed to disk after every account. An outer
crash-recovery loop restarts the run after unexpected errors, so it can be left running
unattended overnight.

**Output:** `data/tweets.json` and `data/tweets.csv` — 9,931 tweets.

### 2. Language filtering — `analyze.ipynb`

Three passes, documented in full with counts in [`reports/data_filter.md`](reports/data_filter.md):

1. **Drop English-only tweets.** Any tweet with zero Devanagari characters
   (`U+0900`–`U+097F`) was removed. Kept 7,102 of 9,931.
2. **Strip Latin script from mixed tweets.** 5,803 of the surviving tweets mixed Nepali
   and English, and 4,510 contained a link. Contiguous Devanagari runs were extracted
   into `text_nepali_only`, discarding English words, digits, Latin hashtags and URLs.
   A validation pass confirmed no Latin characters leaked through.
3. **Drop fragments under 4 words**, measured on the cleaned Nepali text. Kept 6,824.

**Output:** `data/filtered_data.csv` — 6,824 tweets.

### 3. Sentence segmentation — `split_sentences.py`

Tweets frequently contain several distinct opinions, which makes a single sentiment
label for a whole tweet lossy. Each tweet is therefore split on the Nepali danda (`।`)
followed by whitespace, and on newlines, expanding 6,824 tweets into 12,282 sentence
rows. Every row gets a stable `row_id`; `tweet_id` points back to the source tweet and
`sentence_index` gives its position within it.

The script backs up to `data/filtered_data_backup.csv` first and is idempotent — it
detects the `row_id`/`tweet_id` columns and skips if it has already run.

### 4. Sentiment annotation — `app.py`

See below.

---

## The annotation app

A Flask app where three annotators independently label every sentence. Each signs in
with their own number (1, 2 or 3) and password, and works through the corpus on their
phone.

**Label set** — a five-point scale plus an escape hatch:

| Label | English | Nepali |
|---|---|---|
| `strongly_positive` | Strongly Positive | अति सकारात्मक |
| `positive` | Positive | सकारात्मक |
| `neutral` | Neutral | तटस्थ |
| `negative` | Negative | नकारात्मक |
| `strongly_negative` | Strongly Negative | अति नकारात्मक |
| `dont_know` | Don't know | थाहा छैन |

**Design notes**

- **Labels are keyed on `tweet_id:sentence_index`,** never on the row's position in the
  file, so the corpus can be regenerated without labels drifting onto wrong sentences.
- **Labels live in Postgres, not the CSV.** An earlier version wrote a shared
  `sentiment` column back into `filtered_data.csv` on every tap. That cannot represent
  three verdicts per sentence, and with three people labelling at once the read-modify-
  rewrite cycle would silently lose labels. Annotations are now rows in a table keyed by
  `(annotator_id, row_id)`; `filtered_data.csv` is read-only and never modified.
- **Timestamps** are stored as `TIMESTAMPTZ` in UTC, so labelling times are unambiguous.
- **Independent progress.** Each annotator has their own progress bar and resumes at
  their own first unlabelled sentence. They can navigate freely and change any earlier
  label; re-labelling upserts rather than duplicating.
- **Mobile-first.** Single-column buttons with 52px tap targets, verified at a 390px
  viewport. Keys 1–6 and arrow keys work on desktop. Sessions last 60 days, so
  annotators sign in once.
- **Full overlap by design.** All three label all 12,282 sentences, which is what makes
  inter-annotator agreement computable across the whole dataset rather than a sample.

The task definition given to annotators — label definitions, independence requirement,
the quality check and payment terms — is in [`description.md`](description.md), and is
served as a public page at **`/brief`** so annotators can read it before they are given
credentials. The sign-in screen links to it. Edit `templates/brief.html` to change it;
it deploys with the app.

**Monitoring and export** — both guarded by `ADMIN_TOKEN`:

- `/admin?token=…` — progress for all three annotators.
- `/export.csv?token=…` — one row per sentence with `annotator_1`, `annotator_2` and
  `annotator_3` columns, ready for Fleiss' κ or Krippendorff's α without reshaping.

---

## Repository layout

```
├── app.py                  Annotation web app (Flask)
├── templates/
│   ├── brief.html          Public task + payment brief, served at /brief
│   ├── login.html          Annotator sign-in
│   ├── index.html          Labelling screen
│   └── admin.html          Progress dashboard
├── scrape.py               Tweet collection via Twikit
├── split_sentences.py      Tweet → sentence expansion (one-time migration)
├── analyze.ipynb           Filtering pipeline and corpus statistics
├── data/
│   ├── accounts.json       The 20 source accounts
│   ├── tweets.json/.csv    Raw scrape output (9,931 tweets)
│   ├── filtered_data.csv   Annotation corpus (12,282 sentence rows)
│   └── filtered_data_backup.csv   Pre-segmentation snapshot
├── reports/
│   ├── account_details.md  Source accounts, categories, selection rationale
│   ├── data_filter.md      Filtering pipeline with per-stage counts
│   └── limitations.md      (empty — see Limitations below)
├── description.md          Annotation task definition and compensation terms
├── render.yaml             Render deployment blueprint
├── requirements.txt
└── DEPLOY.md               Hosting walkthrough (Render + Neon)
```

## `data/filtered_data.csv` schema

| Column | Description |
|---|---|
| `row_id` | 0-based position in the file. Navigation only — *not* the annotation key |
| *(derived)* `item_id` | `tweet_id:sentence_index`. **Annotations are keyed on this.** Not a column; computed at load |
| `handle` | Source account |
| `id`, `tweet_id` | Original tweet ID |
| `text` | Original tweet text, unmodified |
| `text_nepali_only` | Devanagari runs only, English and URLs stripped |
| `sentence_text` | The single sentence shown to annotators |
| `sentence_index` | Position of this sentence within its tweet (0-based) |
| `created_at`, `likes`, `retweets`, `url` | Tweet metadata |
| `word_count`, `is_valid_nepali_only` | Filtering artefacts |
| `sentiment` | Legacy single-annotator column, **no longer used or written** |

### Updating the corpus mid-annotation

`filtered_data.csv` is the live source of what annotators see. Commit a change to it and
Render redeploys, and the new sentences are served on the next page load.

Annotations are keyed on **`item_id`** — `tweet_id:sentence_index` — not on `row_id`.
That distinction is what makes the file safe to regenerate: rows can be added, dropped,
re-filtered and renumbered, and every existing label stays attached to the sentence it
was actually given for. `row_id` is a position in the file and shifts whenever the file
changes, which is why it is not used as a key.

Two things to preserve when regenerating:

- **`tweet_id` and `sentence_index` must stay stable** for sentences that already exist.
  Re-running `split_sentences.py` on unchanged text reproduces them exactly.
- **Each `(tweet_id, sentence_index)` pair must be unique.** The app refuses to start
  otherwise, rather than let two sentences silently share one label.

If a regenerated CSV drops or alters sentences that were already labelled, those labels
are kept in the database but no longer match anything. `/admin` reports them as orphans
so the loss is visible rather than silent.

---

## Running it

### Locally

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in the passwords
python app.py               # http://localhost:5000
```

Without `DATABASE_URL` set, the app falls back to a local SQLite file
(`annotations.db`), so you can test without touching the real annotations.

### Deployed

Hosted on Render with a Neon Postgres database. Full walkthrough in
[`DEPLOY.md`](DEPLOY.md). Required environment variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon connection string |
| `ANNOTATOR1_PASSWORD`, `ANNOTATOR2_PASSWORD`, `ANNOTATOR3_PASSWORD` | One per annotator |
| `ADMIN_TOKEN` | Guards `/admin` and `/export.csv` |
| `SECRET_KEY` | Session signing; generated by Render. Changing it signs everyone out |

Secrets live in `.env`, which is gitignored and must never be committed.

---

## Limitations

Carried over from the filtering stage (see [`reports/data_filter.md`](reports/data_filter.md)):

- **Script-boundary splitting.** `text_nepali_only` extraction is character-run based,
  not word-boundary aware. A Nepali word glued to an English suffix without a space is
  split at the script boundary rather than kept whole or dropped.
- **Danda as a separate token.** `।` and `॥` are treated as their own runs and
  space-joined, which may affect downstream tokenization where sentence-final
  punctuation needs to stay attached.
- **Word threshold applied post-cleaning.** The ≥4-word filter ran on cleaned Nepali
  text, so a tweet with six mixed-script words but only three Nepali ones was dropped
  despite looking long enough before cleaning.

From sentence segmentation:

- **Short sentences survive the word filter.** The ≥4-word threshold was applied per
  *tweet*, before splitting. Segmentation can therefore produce sentence rows as short
  as one word, which annotators may find unlabelable — `dont_know` exists partly for
  this.
- **Danda-based splitting is naive.** It does not handle abbreviations, quoted speech,
  or sentences that end without a danda, both of which occur in informal tweet text.

From the corpus itself:

- **Speaker skew.** All text comes from 20 prominent public figures, so the register is
  public and rhetorical rather than conversational. Findings should not be generalised
  to everyday Nepali social media speech.
- **Political skew.** 45% of sources are politicians. Party affiliation is recorded in
  [`reports/account_details.md`](reports/account_details.md) and is worth checking
  against annotation bias.
- **Uneven time coverage.** The range spans Dec 2017 – Aug 2026, but tweets are not
  evenly distributed across it, and Nepal's September 2025 social media restrictions
  create a structural gap worth accounting for in any temporal analysis.

---

## Source accounts

20 accounts across three categories, selected for ideological and topical spread.
Full table with roles and selection rationale in
[`reports/account_details.md`](reports/account_details.md).

| Category | Count |
|---|---|
| Politicians & elected officials | 9 |
| Journalists & media figures | 9 |
| Activists & social commentators | 2 |

The politician group spans Nepali Congress, CPN(UML), RSP and the Socialist Party plus
one independent, chosen to limit partisan skew in the resulting sentiment labels.
