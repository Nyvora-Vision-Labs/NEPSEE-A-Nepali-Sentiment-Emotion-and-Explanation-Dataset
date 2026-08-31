# NEPSEE Annotation Software — Design and Build

How the tool that collects the sentiment labels was built, and why it is shaped the way
it is. The corpus pipeline that feeds it is documented separately in `data_filter.md`.

## 1. What it had to do

The dataset needs **three independent judgements on every sentence**, because
inter-annotator agreement is the measurement that makes the labels defensible. That
requirement drove nearly every decision below:

- Three people label the **same** 10,947 sentences, at the same time, without seeing or
  affecting each other's answers.
- Annotators are not technical and are working on their phones, in spare time, over
  weeks. The tool has to survive being closed mid-session and reopened on a different
  device.
- Nothing may be lost. A label given once is a paid unit of work and an irreplaceable
  judgement.
- The researcher needs to watch progress and pull the results out in a shape that goes
  straight into a kappa / Krippendorff's alpha calculation.

Off-the-shelf tools (Label Studio, Doccano, Prodigy) all do more than this and cost
either money or a server to babysit. A single-purpose Flask app was smaller than the
configuration those would have needed.

## 2. Architecture

```
Annotator's phone ──HTTPS──► Render (Flask + gunicorn) ──► Neon Postgres
                                     │                        (labels only)
                                     └── data/filtered_data.csv
                                         (corpus, read-only, from git)
```

The central split: **the corpus is a file in git, the labels are in a database.**

`data/filtered_data.csv` is loaded once into memory at startup and never written to.
Updating the corpus means committing a new CSV and letting Render redeploy — no
migration, no admin screen, no risk of the app corrupting its own input. The database
holds nothing but annotations, so it stays tiny and its schema never has to track
changes in the corpus.

| Piece | Choice | Why |
|---|---|---|
| Web framework | Flask | Four routes and four templates; a heavier framework would be scaffolding around nothing. |
| Database | Neon Postgres (free tier) | Managed, persistent, and free. Concurrent writes from three annotators need a real database, not SQLite on an ephemeral disk. |
| Hosting | Render (free tier) | Deploys from `render.yaml` on git push; no server to maintain. |
| Server | gunicorn, 1 worker × 8 threads | One worker keeps the Neon connection pool small; eight threads is ample for three users. |
| Front end | Server-rendered HTML, no framework | Every action is a form POST. No build step, no JavaScript bundle, nothing to break on an old Android browser. |

Total dependencies: Flask, SQLAlchemy, psycopg, gunicorn, python-dotenv.

## 3. The identity problem — what a label points at

This is the design decision with the most consequence, and it was got wrong first.

The original build keyed each annotation on `row_id`, the row's position in the CSV.
That works right up until the corpus is regenerated. Dropping the 1,335 short sentences
described in `data_filter.md` shifts every row after the first deletion up by one — and
every stored label silently slides onto a **different sentence**. The corruption is
invisible: no error, no crash, just labels that no longer mean what they meant.

Commit `82eee89` re-keyed annotations on a **content identity** instead:

```python
item_id = f"{tweet_id}:{sentence_index}"
```

`tweet_id` is the X status ID and `sentence_index` is the sentence's position within its
own tweet. Neither moves when other rows are added, dropped or reordered. Rows can be
renumbered freely; a label stays attached to the sentence it was given for.

Two guards back this up:

- **Startup check.** Duplicate `item_id`s would make two sentences share one label, so
  the app counts them at boot and refuses to start if any collide, naming the offenders.
  Failing loudly at deploy time beats discovering merged labels at analysis time.
- **Orphan detection.** `/admin` compares every `item_id` in the database against the
  loaded corpus and warns about labels whose sentence has disappeared. That is the
  signal that a corpus update dropped something already judged. When the short-sentence
  filter ran, this reported zero orphans.

`row_id` survives only as a display and export column, which is why it was left with
gaps rather than renumbered after the drop.

## 4. Storing a label

```sql
CREATE TABLE IF NOT EXISTS annotations (
    annotator_id INTEGER NOT NULL,
    item_id      TEXT    NOT NULL,
    label        TEXT    NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (annotator_id, item_id)
)
```

One row per (annotator, sentence). The composite primary key is what enforces
independence structurally: annotator 2's answer cannot overwrite annotator 1's, because
they are different rows.

Writes are a single upsert, so changing an earlier answer is the same operation as
giving one for the first time:

```sql
INSERT INTO annotations (annotator_id, item_id, label, updated_at)
VALUES (:a, :r, :l, :t)
ON CONFLICT (annotator_id, item_id)
DO UPDATE SET label = excluded.label, updated_at = excluded.updated_at
```

Every tap commits immediately — there is no "save" button and no client-side buffer to
lose. `updated_at` is `TIMESTAMPTZ` written from `datetime.now(timezone.utc)`, so pace
can be reconstructed later across time zones; that timing data is what the quality check
described in `description.md` leans on to spot a completion rate too fast to be real.

The table is created by `init_db()` at import time, wrapped in a five-attempt retry with
backoff. Neon's free tier scales to zero, so the first connection after an idle period
can arrive before the database has finished waking up; without the retry a deploy that
happened to land on a sleeping instance would crash on boot.

## 5. Authentication

There are exactly three users and there will never be more, so there is no signup, no
user table and no password reset. Each annotator's password is an environment variable
(`ANNOTATOR1_PASSWORD` … `ANNOTATOR3_PASSWORD`) set in the Render dashboard, compared
with `hmac.compare_digest` to avoid leaking anything through timing. A successful login
puts the annotator's number in a signed Flask session marked permanent, with a **60-day**
lifetime — they sign in once and stay signed in for the duration of the project.

`/admin` and `/export.csv` are guarded differently, by an `ADMIN_TOKEN` query parameter,
and return **404 rather than 403** on a bad or missing token so the endpoints do not
advertise their own existence.

`/brief` is deliberately public: annotators are sent that link to read the task and the
payment terms *before* they are given a number and password, and the login page links to
it for anyone who lands there first.

## 6. The labelling screen

One sentence per screen. The sentence is set large (24px on wider viewports) because it
is the only thing on the page that matters; below it sit the six label buttons, each
carrying its English name, its Nepali name (`अति सकारात्मक`, `तटस्थ`, …) and a number
key, colour-coded green through red with `dont_know` outside the scale.

Decisions worth naming:

- **Resume where you left off.** With no `idx` parameter the app scans for the first
  sentence this annotator has not yet labelled and opens there. Closing the tab and
  coming back later is the normal way to use it, not an edge case.
- **Going back is allowed.** Previous/Next buttons and a jump-to-number box let an
  annotator revisit any sentence. If one already has a label, a banner says so and the
  chosen button is highlighted — tapping another simply replaces it. Early versions were
  forward-only, which meant a mis-tap was permanent; that is a worse failure than the
  small risk of second-guessing.
- **Keyboard shortcuts.** Keys `1`–`6` submit a label and `←`/`→` navigate, so the two
  annotators working at a laptop never touch the mouse. The handler ignores keystrokes
  while an input is focused and any press carrying a modifier.
- **Sentence context.** When a sentence came from a tweet that split into several, a
  badge reads "Sentence 3 of 5", and the source tweet's handle, date and a link to the
  original are shown. Enough context to judge, without showing the neighbouring
  sentences and biasing the label.
- **Progress is always visible.** A bar and an `n / 10,947` tally sit at the top of every
  screen — the work is long, and being able to see it move matters.
- **Phone first.** `viewport-fit=cover`, large tap targets, keyboard hints hidden under
  600px. Annotators are told they can add it to their home screen so it opens like an
  app.

The whole screen is one Jinja template with inline CSS. Every label submission is an
ordinary form POST followed by a redirect to the next index, so the back button behaves
and a flaky mobile connection cannot leave the page in a half-saved state.

## 7. Monitoring and export

`/admin` shows each annotator's count and percentage, the orphan warning described
above, and a download button. `/export.csv` streams a wide format — one row per
sentence, one column per annotator:

```
item_id, row_id, handle, created_at, url, sentence_text,
annotator_1, annotator_2, annotator_3
```

Unlabelled cells are empty rather than absent, so the file is rectangular and loads
directly into pandas for agreement statistics. It is generated as a streaming response
rather than assembled in memory, since it grows to roughly 33,000 labels.

## 8. Deployment

`render.yaml` declares the service, so connecting the repo is the entire setup: Render
reads the build and start commands, generates `SECRET_KEY` itself, and leaves the five
secrets (`DATABASE_URL`, three annotator passwords, `ADMIN_TOKEN`) marked `sync: false`
to be filled in by hand. `.env.example` documents the same set for local work; the real
`.env` is gitignored.

Two accommodations for free-tier infrastructure:

- **Neon scales to zero.** The SQLAlchemy engine uses `pool_pre_ping=True` to discard
  dead connections and `pool_recycle=280` to retire them before the idle timeout, on top
  of the `init_db` retry loop.
- **Render sleeps** after 15 minutes without traffic, so the first request of a session
  can take up to a minute. This is not fixable on the free plan, so `DEPLOY.md` tells the
  coordinator to warn the annotators rather than letting them conclude it is broken.

Locally, an unset `DATABASE_URL` falls back to a SQLite file, so the app can be run and
tested without touching production data. The URL rewriting in `_database_url()` exists
because Neon and Render hand out `postgres://` and `postgresql://` strings while
SQLAlchemy 2 needs the psycopg3 driver named explicitly.

## 9. How it got here

| Commit | What changed |
|---|---|
| `39bd9ee` | First version: single annotator, tweet-level labelling, forward-only, three labels plus `dont_know`, written straight back into a `sentiment` column in the CSV. |
| `5b3f344` | Sentence-level labelling plus back/forward navigation. |
| `bf4bd7d` | Rebuilt for three independent annotators; 5-point scale plus `dont_know`; login and admin pages. |
| `edaf6bd` | `TIMESTAMPTZ` timestamps; `.env` loading for local development. |
| `82eee89` | Re-keyed annotations on `tweet_id:sentence_index`; added the duplicate check and orphan warning. |
| `77730fd` | The annotator brief served at `/brief`. |

Two through-lines. The label scale widened from three points to five plus `dont_know`,
as it became clear that annotators needed somewhere to put emphatic praise and
condemnation that a plain positive/negative split flattened. And storage moved from the
CSV itself — the first version wrote each label into a `sentiment` column and saved the
file, which cannot work once three people are labelling at once — to a database keyed on
a content identity rather than a row number. The now-unused `sentiment` column still
sits in `filtered_data.csv` as a fossil of that first design.

## 10. Known limitations

- **No inter-annotator agreement in the app.** Agreement is computed offline from the
  export. Fine for three annotators; it would need building if the team grew.
- **Passwords are environment variables**, so adding a fourth annotator means a code
  change and a redeploy, not an admin action. Acceptable at three, deliberate.
- **The corpus lives in memory**, loaded once at startup. At 10,947 rows this is
  comfortable; a corpus an order of magnitude larger would need paging or a database.
- **No audit trail of changes.** The upsert overwrites, so only an annotator's latest
  answer and the time it was given survive. Reconstructing how often someone revised a
  judgement is not possible.
- **The orphan check is advisory.** It reports labels stranded by a corpus update but
  does not block the deploy that stranded them; the researcher has to look at `/admin`
  after changing the CSV.
- **Free-tier cold starts** remain the roughest edge of the annotator experience.
