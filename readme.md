# NEPSEE — A Nepali Sentiment, Emotion and Explanation Dataset

## Scripts

- `scrape.py` — scrapes tweets; needs `cookies.json` with your X cookie details.
- `analyze.ipynb` — analysis of the scraped data.
- `split_sentences.py` — splits tweets into individual sentences for annotation.
- `app.py` — the annotation web app (see below).

## Annotation app

A Flask app where three annotators independently label every sentence in
`data/filtered_data.csv` on a five-point sentiment scale:

`strongly_positive` · `positive` · `neutral` · `negative` · `strongly_negative`,
plus `dont_know` for sentences they cannot judge.

Each annotator signs in with their own number (1, 2 or 3) and password. Labels
are written to a database keyed by `(annotator_id, row_id)`, so the three of
them can work at the same time and the CSV is never modified.

See [DEPLOY.md](DEPLOY.md) for hosting and for how to export the results.
