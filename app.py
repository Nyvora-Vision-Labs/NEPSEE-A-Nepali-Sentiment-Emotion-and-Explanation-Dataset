from pathlib import Path
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

CSV_PATH = Path("data/filtered_data.csv")
SENTIMENT_COLUMN = "sentiment"
VALID_LABELS = {"positive", "neutral", "negative", "dont_know"}


def load_df() -> pd.DataFrame:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {CSV_PATH}. Place filtered_data.csv in the data/ folder."
        )
    # Ensure all columns are read as strings to preserve tweet IDs and formatting
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


@app.route("/")
def index():
    df = load_df()
    unlabeled = df[df[SENTIMENT_COLUMN] == ""]
    progress = get_progress(df)

    if unlabeled.empty:
        return render_template("index.html", done=True, progress=progress)

    row = unlabeled.iloc[0]

    tweet_text = row.get("text_nepali_only")
    if pd.isna(tweet_text) or not str(tweet_text).strip():
        tweet_text = row.get("text", "")

    tweet = {
        "id": str(row["id"]),
        "handle": str(row.get("handle", "")),
        "text": str(tweet_text),
        "created_at": str(row.get("created_at", "")),
        "likes": str(row.get("likes", "")),
        "retweets": str(row.get("retweets", "")),
        "url": str(row.get("url", "")),
    }

    return render_template(
        "index.html",
        done=False,
        tweet=tweet,
        progress=progress,
    )

#route
@app.route("/rate", methods=["POST"])
def rate():
    tweet_id = request.form.get("tweet_id")
    label = request.form.get("label")

    if label not in VALID_LABELS:
        return "Invalid label", 400

    df = load_df()
    match = df["id"].astype(str) == str(tweet_id)

    if not match.any():
        return "Tweet ID not found in CSV.", 404

    df.loc[match, SENTIMENT_COLUMN] = label
    save_df(df)

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)