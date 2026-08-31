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

The corpus currently holds **10,947 sentences** — down from 12,282 after sentence
fragments of fewer than five words were removed — and may grow modestly with further
scraping before annotation begins. Each annotator labels all of them.

## Payment

**Rs 1 per annotation**, up to a maximum of **11,000 annotations**, paid per annotator,
**on completion of the full set**.

> **Maximum payable per annotator: Rs 11,000, or USD 65, whichever is higher at the
> time of payment.** This is the ceiling regardless of how large the corpus becomes.

Payment is conditional on finishing. An annotator who stops before labelling every
sentence is not paid for the sentences they did label. This must be stated to each
annotator before they begin, not at the point they want to stop.

Genuine emergencies are the exception. Illness, a family emergency or anything else
outside the annotator's control is handled personally by the project lead, case by
case. Annotators should be told to raise it directly rather than simply stopping.

The total is then whichever of these two is **higher at the time of completion**:

- **Rs 11,000**, or
- **USD 65**, converted to Nepali rupees at the exchange rate on the completion date.

The second arm exists so that the value of the payment does not fall if the rupee
weakens over the course of the work. Which arm applies depends on the rate on the day:

| NPR per USD on completion date | USD 65 equals | Amount paid |
|---|---|---|
| 140 | Rs 9,100 | **Rs 11,000** (rupee amount is higher) |
| 160 | Rs 10,400 | **Rs 11,000** (rupee amount is higher) |
| 170 | Rs 11,050 | **Rs 11,050** (dollar amount is higher) |
| 185 | Rs 12,025 | **Rs 12,025** (dollar amount is higher) |

The two arms cross at roughly **NPR 169 per USD** — below that the rupee figure governs,
above it the dollar figure does.

*Illustrative only — the actual rate on the completion date governs.*

Payment is per annotator, so three annotators completing the full corpus costs
Rs 33,000 in total, or the dollar equivalent if that is higher.

### Quality check

Payment is also conditional on the work passing a check once all three annotators have
finished. The three sets of answers are compared against each other, and an annotator
whose work fails the check is not paid.

The check is aimed at work that does not represent genuine judgement — labels diverging
from both other annotators far beyond the normal range, long runs of a single label,
or a completion pace that leaves no time to have read the sentences.

Ordinary disagreement is not a failure. Three people will not agree on every sentence,
and measuring how often they do is the entire reason three annotators are used. An
annotator who is simply stricter than the others — reaching for Strongly Negative where
they reach for Negative — is internally consistent, statistically correctable, and has
done the job properly.

The threshold that separates the two must be fixed and communicated **before** work
begins. Deciding after the fact what counts as "too far off" is both unfair to the
annotator and, because they cannot know what they are being held to, unenforceable in
practice. It also creates the incentive this rule most needs to avoid: if diverging from
the majority is what costs an annotator their payment, the safe strategy is to guess
what the other two would say rather than record an honest judgement — which destroys the
independence the dataset depends on.

### Worked examples

- Annotator labels all 10,947 sentences → 10,947 × Rs 1 = Rs 10,947, then compared
  against USD 65 and the higher amount is paid.
- Annotator labels 9,000 sentences and stops → **no payment**. The work is paid on
  completion, not per sentence delivered, so partial work earns nothing.
- Corpus ends up at 13,000 sentences and the annotator labels all of them → payment
  is capped at 11,000 annotations, so Rs 11,000, compared against USD 65 as above.
- Annotator finishes the full set but the work fails the quality check → **no payment**,
  on the same basis as not finishing.

`Don't know` responses count as annotations and are paid exactly the same as any other
label. They are a real judgement about the sentence, and paying less for them would
create a reason to guess.

That said, the sentences have been filtered and prepared so that the large majority are
judgeable by a native speaker. `Don't know` is there for the genuinely ambiguous
fragment, and should be a small share of an annotator's answers rather than a routine
escape. If someone is reaching for it constantly, something is wrong with the data or
with their understanding of the task, and it is worth catching early.

## Points to confirm before work begins

These follow from the terms above but are worth agreeing explicitly, in writing, with
all three annotators:

1. **Which exchange rate** settles the USD comparison — Nepal Rastra Bank's published
   rate for the completion date is the obvious neutral choice.
2. **What "completion" means** — the date the annotator finishes their last sentence,
   or the date all three finish. These can differ by weeks.
3. **What counts as finishing**, given that payment is all-or-nothing — in particular
   whether an annotator who reaches the end with some sentences left on `Don't know`
   has completed the set.
4. **The quality-check threshold**, stated concretely enough that an annotator knows
   what they are being held to before they start, and agreed with all three of them.
5. **What happens if the corpus grows after someone finishes** — whether they are
   asked to label the new sentences, and whether that is paid beyond the 11,000 cap.
6. **Payment timing and method.**

## Data handling

Tweets are public posts by public figures, collected from X. Annotators see only the
sentence text and its public metadata. No private or personal data is involved.

Annotation labels are stored against sentence identifiers, alongside the annotator
number and a timestamp. Annotators should be told that their individual labels are
recorded separately and will be used to compute inter-annotator agreement, and whether
their labels will be published attributed by number in any released dataset.
