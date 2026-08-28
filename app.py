from pathlib import Path
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

CSV_PATH = Path("data/filtered_data.csv")
SENTIMENT_COLUMN = "sentiment"
VALID_LABELS = {"positive", "neutral", "negative", "dont_know"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_df() -> pd.DataFrame:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {CSV_PATH}. Place filtered_data.csv in the data/ folder."
        )
    df = pd.read_csv(CSV_PATH, dtype=str, encoding="utf-8")

    if SENTIMENT_COLUMN not in df.columns:
        df[SENTIMENT_COLUMN] = ""

    df[SENTIMENT_COLUMN] = df[SENTIMENT_COLUMN].fillna("")
    return df


def save_df(df: pd.DataFrame) -> None:
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")


def get_progress(df: pd.DataFrame) -> dict:
    total = len(df)
    labeled = int((df[SENTIMENT_COLUMN] != "").sum())
    return {
        "total": total,
        "labeled": labeled,
        "remaining": total - labeled,
        "percent": round((labeled / total * 100), 1) if total > 0 else 0,
    }


def row_to_tweet(row: pd.Series, idx: int, df: pd.DataFrame) -> dict:
    """Convert a DataFrame row into a tweet dict for the template."""
    # Prefer the pre-split sentence_text column when available
    text = row.get("sentence_text", "")
    if pd.isna(text) or not str(text).strip():
        text = row.get("text_nepali_only", "")
    if pd.isna(text) or not str(text).strip():
        text = row.get("text", "")

    tweet_id = str(row.get("row_id", idx))  # use stable row_id when present

    # Sentence context indicator e.g. "(sentence 2 of 3)"
    sentence_index = row.get("sentence_index", None)
    tweet_id_orig = str(row.get("tweet_id", row.get("id", "")))

    # Count how many sub-rows share the same original tweet_id
    if "tweet_id" in df.columns and "sentence_index" in df.columns:
        siblings = df[df["tweet_id"] == tweet_id_orig]
        total_sentences = len(siblings)
        sentence_num = int(sentence_index) + 1 if pd.notna(sentence_index) else 1
    else:
        total_sentences = 1
        sentence_num = 1

    return {
        "id": tweet_id,
        "handle": str(row.get("handle", "")),
        "text": str(text),
        "created_at": str(row.get("created_at", "")),
        "likes": str(row.get("likes", "")),
        "retweets": str(row.get("retweets", "")),
        "url": str(row.get("url", "")),
        "sentiment": str(row.get(SENTIMENT_COLUMN, "")),
        "sentence_num": sentence_num,
        "total_sentences": total_sentences,
        "idx": idx,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    df = load_df()
    progress = get_progress(df)

    # Allow explicit index navigation via ?idx=N
    idx_param = request.args.get("idx")

    if idx_param is not None:
        try:
            idx = int(idx_param)
            idx = max(0, min(idx, len(df) - 1))
        except ValueError:
            idx = None

    if idx_param is None:
        # Default: find the first unlabeled row
        unlabeled_indices = df.index[df[SENTIMENT_COLUMN] == ""].tolist()
        if not unlabeled_indices:
            return render_template("index.html", done=True, progress=progress)
        idx = unlabeled_indices[0]

    row = df.iloc[idx]
    tweet = row_to_tweet(row, idx, df)

    prev_idx = idx - 1 if idx > 0 else None
    next_idx = idx + 1 if idx < len(df) - 1 else None

    return render_template(
        "index.html",
        done=False,
        tweet=tweet,
        progress=progress,
        prev_idx=prev_idx,
        next_idx=next_idx,
        current_idx=idx,
    )


@app.route("/rate", methods=["POST"])
def rate():
    row_id = request.form.get("tweet_id")   # this is actually the row_id / idx
    label = request.form.get("label")
    current_idx = request.form.get("current_idx", type=int, default=0)

    if label not in VALID_LABELS:
        return "Invalid label", 400

    df = load_df()

    # Prefer matching on row_id column (stable after migration)
    if "row_id" in df.columns:
        match = df["row_id"].astype(str) == str(row_id)
    else:
        match = df["id"].astype(str) == str(row_id)

    if not match.any():
        return "Row ID not found in CSV.", 404

    df.loc[match, SENTIMENT_COLUMN] = label
    save_df(df)

    # After rating, advance to next row
    next_idx = current_idx + 1
    if next_idx >= len(df):
        return redirect(url_for("index"))
    return redirect(url_for("index", idx=next_idx))


if __name__ == "__main__":
    app.run(debug=True, port=5000)