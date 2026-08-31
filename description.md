# NEPSEE — Annotation Task and Compensation

## The task

Read a single Nepali sentence and judge the sentiment the writer is expressing.
Sentences come from tweets by 20 Nepali public figures — politicians, journalists
and activists — writing about politics, governance and current affairs.

Each sentence gets exactly one of six labels:

| Label | Nepali | Use when |
|---|---|---|
| Strongly Positive | अति सकारात्मक | Emphatic praise, celebration, strong approval |
| Positive | सकारात्मक | Mild approval, optimism, good news stated plainly |
| Neutral | तटस्थ | Factual statement, announcement, no evident stance |
| Negative | नकारात्मक | Mild criticism, disappointment, concern |
| Strongly Negative | अति नकारात्मक | Emphatic condemnation, anger, accusation |
| Don't know | थाहा छैन | Too short, ambiguous, or lacking context to judge |

Judge the sentiment **expressed in the sentence**, not whether you agree with it and
not whether the underlying event is good or bad news. A sentence can report a
terrible event in neutral, factual language.

`Don't know` is a legitimate answer, not a failure. Sentences are split at the Nepali
danda (`।`), so some are fragments of a few words that genuinely cannot be judged on
their own. Use it rather than guessing — a guessed label is worse than no label.

## How the work is organised

Three annotators, numbered 1, 2 and 3. Each is given their own number and password
and works through **the entire corpus independently**. All three label every sentence.

Annotators must not discuss individual sentences or compare answers while working.
The scientific value of the dataset comes from three genuinely independent judgements
per sentence — agreement between them is a measurement, and it stops being one if the
judgements influence each other.

Work is saved after every tap. You can stop at any point and resume where you left
off, on any device. You can also go back and change an earlier answer.

## Scope

The corpus currently holds **12,282 sentences** and is expected to grow to roughly
**15,000** before annotation begins. Each annotator labels all of them.

## Payment

**Rs 1 per annotation**, up to a maximum of **15,000 annotations**, paid per annotator,
**on completion of the full set**.

Payment is conditional on finishing. An annotator who stops before labelling every
sentence is not paid for the sentences they did label. This must be stated to each
annotator before they begin, not at the point they want to stop.

The total is then whichever of these two is **higher at the time of completion**:

- **Rs 15,000**, or
- **USD 100**, converted to Nepali rupees at the exchange rate on the completion date.

The second arm exists so that the value of the payment does not fall if the rupee
weakens over the course of the work. Which arm applies depends on the rate on the day:

| NPR per USD on completion date | USD 100 equals | Amount paid |
|---|---|---|
| 135 | Rs 13,500 | **Rs 15,000** (rupee amount is higher) |
| 145 | Rs 14,500 | **Rs 15,000** (rupee amount is higher) |
| 150 | Rs 15,000 | Rs 15,000 (equal) |
| 160 | Rs 16,000 | **Rs 16,000** (dollar amount is higher) |

*Illustrative only — the actual rate on the completion date governs.*

Payment is per annotator, so three annotators completing the full corpus costs
Rs 45,000 in total, or the dollar equivalent if that is higher.

### Worked examples

- Annotator labels all 15,000 sentences → 15,000 × Rs 1 = Rs 15,000, then compared
  against USD 100 and the higher amount is paid.
- Annotator labels 9,000 sentences and stops → **no payment**. The work is paid on
  completion, not per sentence delivered, so partial work earns nothing.
- Corpus ends up at 16,000 sentences and the annotator labels all of them → payment
  is capped at 15,000 annotations, so Rs 15,000, compared against USD 100 as above.

`Don't know` responses count as annotations and are paid the same as any other label.
They are a real judgement about the sentence, and paying less for them would create a
reason to guess.

## Points to confirm before work begins

These follow from the terms above but are worth agreeing explicitly, in writing, with
all three annotators:

1. **Which exchange rate** settles the USD comparison — Nepal Rastra Bank's published
   rate for the completion date is the obvious neutral choice.
2. **What "completion" means** — the date the annotator finishes their last sentence,
   or the date all three finish. These can differ by weeks.
3. **What counts as finishing**, given that payment is all-or-nothing. Whether an
   annotator who reaches the end with some sentences left on `Don't know` has
   completed the set, and whether illness or a family emergency partway through is
   handled differently from simply stopping.
4. **What happens if the corpus grows after someone finishes** — whether they are
   asked to label the new sentences, and whether that is paid beyond the 15,000 cap.
5. **Payment timing and method.**

## Data handling

Tweets are public posts by public figures, collected from X. Annotators see only the
sentence text and its public metadata. No private or personal data is involved.

Annotation labels are stored against sentence identifiers, alongside the annotator
number and a timestamp. Annotators should be told that their individual labels are
recorded separately and will be used to compute inter-annotator agreement, and whether
their labels will be published attributed by number in any released dataset.
