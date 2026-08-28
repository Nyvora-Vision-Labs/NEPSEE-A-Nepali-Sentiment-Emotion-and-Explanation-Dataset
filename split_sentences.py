"""
split_sentences.py
------------------
One-time migration: expand rows that contain multiple Nepali sentences
(separated by ।) into individual rows, each with their own `row_id` and a
`tweet_id` pointing back to the original tweet.

Run:  python3 split_sentences.py
"""

from pathlib import Path
import pandas as pd
import re
import shutil

CSV_PATH = Path("data/filtered_data.csv")
BACKUP_PATH = Path("data/filtered_data_backup.csv")


def split_sentences(text: str) -> list[str]:
    if not text or str(text).strip() in ("", "nan"):
        return [str(text).strip()]
    text = str(text).strip()
    # Split on Nepali danda (।) followed by whitespace/newline, or on newlines alone
    parts = re.split(r"(?<=।)\s+|\n+", text)
    parts = [p.strip() for p in parts if p.strip()]
    return parts if parts else [text]


def main():
    print(f"Loading {CSV_PATH} …")
    df = pd.read_csv(CSV_PATH, dtype=str, encoding="utf-8")
    df["sentiment"] = df["sentiment"].fillna("")

    # Back up before touching anything
    shutil.copy(CSV_PATH, BACKUP_PATH)
    print(f"Backup written to {BACKUP_PATH}")

    # If we already ran this script, `row_id` and `tweet_id` columns exist –
    # skip expansion to stay idempotent.
    if "row_id" in df.columns and "tweet_id" in df.columns:
        print("Columns row_id / tweet_id already present – nothing to do.")
        return

    rows_out = []
    for _, row in df.iterrows():
        # Use text_nepali_only preferentially; fall back to text
        raw = row.get("text_nepali_only", "")
        if pd.isna(raw) or str(raw).strip() == "":
            raw = row.get("text", "")

        sentences = split_sentences(str(raw))

        if len(sentences) == 1:
            new_row = row.to_dict()
            new_row["tweet_id"] = str(row["id"])
            new_row["sentence_text"] = sentences[0]
            new_row["sentence_index"] = 0
            rows_out.append(new_row)
        else:
            for i, sentence in enumerate(sentences):
                new_row = row.to_dict()
                new_row["tweet_id"] = str(row["id"])
                new_row["sentence_text"] = sentence
                new_row["sentence_index"] = i
                # Only the first sub-row inherits any pre-existing sentiment;
                # additional sub-rows start blank so each sentence gets annotated.
                if i > 0:
                    new_row["sentiment"] = ""
                rows_out.append(new_row)

    expanded = pd.DataFrame(rows_out)

    # Add a stable row_id for index-based navigation (0-based integer)
    expanded = expanded.reset_index(drop=True)
    expanded.insert(0, "row_id", expanded.index.astype(str))

    print(
        f"Expanded {len(df)} original rows → {len(expanded)} sentence rows "
        f"({len(expanded) - len(df)} new rows added)"
    )

    expanded.to_csv(CSV_PATH, index=False, encoding="utf-8")
    print("Saved expanded CSV.")


if __name__ == "__main__":
    main()
