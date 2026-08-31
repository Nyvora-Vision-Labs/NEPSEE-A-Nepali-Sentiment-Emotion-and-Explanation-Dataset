"""NEPSEE sentiment annotation app.

Three annotators each label the full dataset independently. Texts are read
from data/filtered_data.csv (read-only); labels live in a database so the
three of them can work at the same time without clobbering each other.
"""
import csv
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    Response,
)
from sqlalchemy import create_engine, text

try:  # Local development convenience; on Render the env vars are already set.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

CSV_PATH = Path(os.environ.get("CSV_PATH", "data/filtered_data.csv"))

# Ordered from most positive to most negative; dont_know sits outside the scale.
LABELS = [
    ("strongly_positive", "Strongly Positive", "अति सकारात्मक"),
    ("positive", "Positive", "सकारात्मक"),
    ("neutral", "Neutral", "तटस्थ"),
    ("negative", "Negative", "नकारात्मक"),
    ("strongly_negative", "Strongly Negative", "अति नकारात्मक"),
    ("dont_know", "Don't know", "थाहा छैन"),
]
VALID_LABELS = {key for key, _, _ in LABELS}
LABEL_NAMES = {key: en for key, en, _ in LABELS}

ANNOTATOR_IDS = (1, 2, 3)


# ---------------------------------------------------------------------------
# App / database setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(days=60)


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        # Local development fallback.
        return "sqlite:///annotations.db"
    # Neon/Render hand out postgres:// or postgresql:// URLs; SQLAlchemy needs
    # the psycopg3 driver spelled out explicitly.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


engine = create_engine(
    _database_url(),
    pool_pre_ping=True,   # Neon scales to zero; revive dead connections
    pool_recycle=280,
    future=True,
)


CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS annotations (
        annotator_id INTEGER NOT NULL,
        item_id      TEXT    NOT NULL,
        label        TEXT    NOT NULL,
        updated_at   TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (annotator_id, item_id)
    )
"""


def init_db(attempts: int = 5) -> None:
    """Create the annotations table, retrying while a sleeping Neon instance wakes."""
    for attempt in range(1, attempts + 1):
        try:
            with engine.begin() as conn:
                conn.execute(text(CREATE_TABLE_SQL))
            return
        except Exception as exc:  # noqa: BLE001 - retry on any connection failure
            if attempt == attempts:
                raise
            app.logger.warning(
                "Database not ready (attempt %d/%d): %s", attempt, attempts, exc
            )
            time.sleep(2 * attempt)


# ---------------------------------------------------------------------------
# Corpus (loaded once at startup; the CSV is never written to)
# ---------------------------------------------------------------------------

def load_rows() -> list[dict]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {CSV_PATH}. Place filtered_data.csv in the data/ folder."
        )
    with CSV_PATH.open(encoding="utf-8", newline="") as fh:
        raw = list(csv.DictReader(fh))

    # How many sentences each original tweet was split into.
    sentence_counts: dict[str, int] = {}
    for r in raw:
        tid = (r.get("tweet_id") or "").strip()
        if tid:
            sentence_counts[tid] = sentence_counts.get(tid, 0) + 1

    rows = []
    for i, r in enumerate(raw):
        text_value = ""
        for column in ("sentence_text", "text_nepali_only", "text"):
            candidate = (r.get(column) or "").strip()
            if candidate:
                text_value = candidate
                break
        if not text_value:
            continue

        tid = (r.get("tweet_id") or "").strip()
        try:
            sentence_num = int(r.get("sentence_index") or 0) + 1
        except ValueError:
            sentence_num = 1

        sentence_index = (r.get("sentence_index") or "0").strip()
        # Annotations are keyed on this, NOT on the row's position in the file.
        # tweet_id + sentence_index survives re-filtering, reordering and
        # regenerating the CSV; row_id (a positional index) does not.
        item_id = f"{tid}:{sentence_index}" if tid else "row:" + (r.get("row_id") or str(i)).strip()

        rows.append(
            {
                "item_id": item_id,
                "row_id": (r.get("row_id") or str(i)).strip(),
                "handle": (r.get("handle") or "").strip(),
                "text": text_value,
                "created_at": (r.get("created_at") or "").strip(),
                "url": (r.get("url") or "").strip(),
                "sentence_num": sentence_num,
                "total_sentences": sentence_counts.get(tid, 1),
            }
        )
    return rows


ROWS = load_rows()
ROW_INDEX = {r["item_id"]: i for i, r in enumerate(ROWS)}
TOTAL = len(ROWS)

# A duplicate item_id would make two sentences share one label. Fail loudly at
# startup rather than silently merging them.
if len(ROW_INDEX) != TOTAL:
    from collections import Counter

    dupes = [k for k, n in Counter(r["item_id"] for r in ROWS).items() if n > 1]
    raise SystemExit(
        f"{TOTAL - len(ROW_INDEX)} duplicate item_id(s) in {CSV_PATH}, e.g. {dupes[:5]}. "
        "Each (tweet_id, sentence_index) pair must be unique."
    )


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def password_for(annotator_id: int) -> str:
    return os.environ.get(f"ANNOTATOR{annotator_id}_PASSWORD", "")


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        annotator_id = session.get("annotator_id")
        if annotator_id not in ANNOTATOR_IDS:
            return redirect(url_for("login", next=request.path))
        g.annotator_id = annotator_id
        return view(*args, **kwargs)

    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        raw_id = (request.form.get("annotator_id") or "").strip()
        supplied = request.form.get("password") or ""
        try:
            annotator_id = int(raw_id)
        except ValueError:
            annotator_id = 0

        expected = password_for(annotator_id) if annotator_id in ANNOTATOR_IDS else ""
        if expected and hmac.compare_digest(supplied, expected):
            session.permanent = True
            session["annotator_id"] = annotator_id
            return redirect(request.args.get("next") or url_for("index"))
        error = "Wrong annotator number or password."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Annotation storage
# ---------------------------------------------------------------------------

def labels_for(annotator_id: int) -> dict[str, str]:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT item_id, label FROM annotations WHERE annotator_id = :a"),
            {"a": annotator_id},
        )
        return {item_id: label for item_id, label in result}


def save_label(annotator_id: int, item_id: str, label: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO annotations (annotator_id, item_id, label, updated_at)
                VALUES (:a, :r, :l, :t)
                ON CONFLICT (annotator_id, item_id)
                DO UPDATE SET label = excluded.label, updated_at = excluded.updated_at
                """
            ),
            {
                "a": annotator_id,
                "r": item_id,
                "l": label,
                "t": datetime.now(timezone.utc),
            },
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def index():
    annotator_id = g.annotator_id
    done_labels = labels_for(annotator_id)
    labeled = len(done_labels)

    idx_param = request.args.get("idx")
    idx = None
    if idx_param is not None:
        try:
            idx = max(0, min(int(idx_param), TOTAL - 1))
        except ValueError:
            idx = None

    if idx is None:
        # Jump to the first row this annotator has not labeled yet.
        idx = next(
            (i for i, r in enumerate(ROWS) if r["item_id"] not in done_labels),
            None,
        )
        if idx is None:
            return render_template(
                "index.html",
                done=True,
                annotator_id=annotator_id,
                progress={"labeled": labeled, "total": TOTAL, "percent": 100.0},
            )

    row = ROWS[idx]
    return render_template(
        "index.html",
        done=False,
        annotator_id=annotator_id,
        tweet=row,
        current_label=done_labels.get(row["item_id"], ""),
        labels=LABELS,
        current_idx=idx,
        prev_idx=idx - 1 if idx > 0 else None,
        next_idx=idx + 1 if idx < TOTAL - 1 else None,
        progress={
            "labeled": labeled,
            "total": TOTAL,
            "percent": round(labeled / TOTAL * 100, 1) if TOTAL else 0,
        },
    )


@app.route("/rate", methods=["POST"])
@login_required
def rate():
    item_id = (request.form.get("item_id") or "").strip()
    label = request.form.get("label")
    current_idx = request.form.get("current_idx", type=int, default=0)

    if label not in VALID_LABELS:
        return "Invalid label", 400
    if item_id not in ROW_INDEX:
        return "Unknown item", 404

    save_label(g.annotator_id, item_id, label)

    next_idx = current_idx + 1
    if next_idx >= TOTAL:
        return redirect(url_for("index"))
    return redirect(url_for("index", idx=next_idx))


def _check_admin() -> None:
    expected = os.environ.get("ADMIN_TOKEN", "")
    supplied = request.args.get("token", "")
    if not expected or not hmac.compare_digest(supplied, expected):
        abort(404)


@app.route("/admin")
def admin():
    """Progress overview for the researcher. Guarded by ?token=ADMIN_TOKEN."""
    _check_admin()
    with engine.connect() as conn:
        counts = dict(
            conn.execute(
                text(
                    "SELECT annotator_id, COUNT(*) FROM annotations GROUP BY annotator_id"
                )
            ).all()
        )
    stats = [
        {
            "annotator_id": a,
            "labeled": counts.get(a, 0),
            "percent": round(counts.get(a, 0) / TOTAL * 100, 1) if TOTAL else 0,
        }
        for a in ANNOTATOR_IDS
    ]

    # Labels whose sentence is no longer in the CSV — the signal that a
    # regenerated dataset dropped or altered rows people had already judged.
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT DISTINCT item_id FROM annotations")).scalars().all()
    orphans = sorted(set(stored) - set(ROW_INDEX))

    return render_template(
        "admin.html",
        stats=stats,
        total=TOTAL,
        orphans=orphans,
        token=request.args.get("token", ""),
    )


@app.route("/export.csv")
def export_csv():
    """Wide export: one row per item, one column per annotator."""
    _check_admin()
    per_annotator = {a: labels_for(a) for a in ANNOTATOR_IDS}

    def generate():
        header = [
            "item_id",
            "row_id",
            "handle",
            "created_at",
            "url",
            "sentence_text",
            "annotator_1",
            "annotator_2",
            "annotator_3",
        ]
        yield ",".join(header) + "\n"
        for row in ROWS:
            values = [
                row["item_id"],
                row["row_id"],
                row["handle"],
                row["created_at"],
                row["url"],
                row["text"],
                per_annotator[1].get(row["item_id"], ""),
                per_annotator[2].get(row["item_id"], ""),
                per_annotator[3].get(row["item_id"], ""),
            ]
            yield ",".join('"' + str(v).replace('"', '""') + '"' for v in values) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=nepsee_annotations.csv"},
    )


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
