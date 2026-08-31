"""
drop_short_sentences.py
-----------------------
Remove sentence rows that are too short to carry usable sentiment
(fragments like 'जय नेपाल' or 'राधे').

Run after split_sentences.py:  python3 drop_short_sentences.py

Annotations are keyed on tweet_id:sentence_index, so dropping rows never
orphans an existing label — the surviving rows keep their identity.
`row_id` is left untouched (gaps are fine; it is only carried into exports).
"""

from pathlib import Path
import pandas as pd

CSV_PATH = Path("data/filtered_data.csv")
MIN_WORDS = 5


def main():
    df = pd.read_csv(CSV_PATH, dtype=str, encoding="utf-8")
    before = len(df)

    words = df["sentence_text"].fillna("").str.split().map(len)
    kept = df[words >= MIN_WORDS]

    print(f"{before} rows → {len(kept)} rows ({before - len(kept)} dropped, <{MIN_WORDS} words)")
    kept.to_csv(CSV_PATH, index=False, encoding="utf-8")
    print(f"Saved {CSV_PATH}")


if __name__ == "__main__":
    main()
