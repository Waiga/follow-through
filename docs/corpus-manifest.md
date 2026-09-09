# Corpus manifest

Every number in the README's evidence section was produced against the material
described here. This document exists so that a stranger can obtain the same
material and check.

Where something was not recorded at the time, this document says so rather than
reconstructing it. It also corrects one thing the README implies and should not.

## ⚠️ Read this first: the labellers were not people

The README says the 800 sentences were marked by "labellers who had not seen the
source code", and that "a second labeller re-marked 200 of them without seeing
the first set". Both statements are true about the *procedure*. Neither says who
the labellers were, and the natural reading — human annotators, and therefore a
human inter-annotator agreement figure — is wrong.

**No human labelled any of the 800 sentences.** Every label was produced by an
isolated large-language-model subagent. Specifically, five separate dispatches of
the same model (Claude Opus), each started fresh with no other context and each
instructed not to read the source code, not to look for any tool that classifies
these sentences, and not to look for any other label file:

| dispatch | input | sentences | output |
|---|---|---|---|
| 1 | `control_sample.txt` | 200 (the pilot) | the pilot labels |
| 2 | `control_sample2_part0.txt` | 200 | expansion part 0 |
| 3 | `control_sample2_part1.txt` | 200 | expansion part 1 |
| 4 | `control_sample2_part2.txt` | 200 | expansion part 2 |
| 5 | `control_sample2_part1.txt` again | 200 | the re-label, for agreement |

What this changes about the evidence, stated plainly:

- The isolation is real. The labelling prompts define the task from linguistic
  criteria and worked examples only, they never mention this tool, and they
  forbid looking for its answers. A labeller could not have copied the tool.
- **The independence is weaker than the README implies.** The labels come from
  the same model family that wrote the tool being graded. "A tool must not be
  allowed to grade itself" is the stated reason for this measurement, and an
  LLM-labelled ground truth satisfies that requirement less completely than
  human annotation would.
- **Cohen's kappa 0.92 is not human inter-annotator agreement.** It measures
  agreement between two runs of the same model on the same prompt over the same
  200 sentences. Read it as prompt and rubric stability, not as evidence that
  the labelling rubric is one two people would apply the same way.

The README's wording has been left exactly as published rather than edited here,
because changing a published claim is a separate decision from documenting it.
This section is the correction of record until that decision is made.

## 1. The corpus: 6,320 public meeting records

**What it is.** 5,733 IETF working-group minutes and 587 United States
congressional hearing transcripts, 184 MB, collected 7 September 2026. Neither
body of documents was written for this tool, and no example in this repository
came from either.

**The list.** [`docs/corpus/documents.tsv`](corpus/documents.tsv) — 6,320 rows
plus a header:

| column | meaning |
|---|---|
| `corpus` | `ietf` or `us-congress` |
| `local_name` | the filename the measurement scripts referred to |
| `bytes` | size of the local copy |
| `sha256` | SHA-256 of the local copy |
| `source_url` | where the document came from |

Every row carries a URL. The `sha256` needs one qualification per corpus, given
under each heading below.

### IETF working-group minutes — 5,733 documents

**Selection rule.** The IETF publishes a machine-readable catalogue of meeting
materials. Every entry whose name matches `minutes-<meeting number>-*` and whose
file extension is `.txt` or `.md` was fetched; everything else was skipped, which
excludes slides, agendas, and minutes published only as PDF or HTML. A response
under 200 bytes was discarded as a stub. 5,746 entries matched the rule; 5,733
were obtained.

**Where.** `https://www.ietf.org/proceedings/<meeting>/minutes/<file>` — the
exact URL for every document is in the manifest.

**Range.** IETF 65 (2006) to IETF 126 (2026). The meeting number is the first
numeric field of the filename, so the distribution is readable straight from the
manifest.

**Hashes.** The bytes as served. These files were written to disk unmodified, so
`sha256` is directly comparable against a fresh download.

**Licence.** IETF meeting minutes are IETF Trust material, published as part of
the IETF's public proceedings. **The documents are not redistributed here** —
only their names, URLs and hashes.

### United States congressional hearings — 587 documents

**Selection rule, exactly, including its seed.** For each of the years 2016,
2018, 2019, 2021, 2022, 2023 and 2024, the GovInfo sitemap
`https://www.govinfo.gov/sitemap/CHRG_<year>_sitemap.xml` was read and every
`CHRG-…` package ID extracted. The combined list was shuffled with Python's
`random.seed(11)` and the first 600 taken. A response whose extracted text was
under 3,000 characters was discarded. 587 of the 600 were obtained.

**Note the year list.** It is seven specific years, **not** a continuous range.
2017 and 2020 are absent. The README describes the set as "587 United States
congressional hearing transcripts from 2016 to 2024"; the seven years above are
what was actually sampled. By Congress, the 587 fall out as: 114th — 75, 115th —
60, 116th — 114, 117th — 173, 118th — 165.

**Where.** `https://www.govinfo.gov/content/pkg/<ID>/html/<ID>.htm`.

**⚠️ Hashes for this corpus are of a derived file, not of the served bytes.**
GovInfo serves these as HTML. The fetch stripped every tag with the regular
expression `<[^>]+>` and then applied `html.unescape`, and wrote the result as
UTF-8. That plain-text file is what was measured and what the `sha256` column
describes. Re-running those two transformations on a fresh download reproduces
it; hashing the served HTML does not.

**Reproducibility caveat on the seed.** `seed(11)` makes the draw deterministic
*given the same input list in the same order*. GovInfo sitemaps change as
packages are added, so the same code run today may not select the same 600. The
manifest is the authority on which 587 were used; the seed records how they were
chosen, not a guarantee that the choice repeats.

**Licence.** Works of the United States Government, in the public domain. Not
redistributed here — names, URLs and hashes only.

## 2. The 800 labelled sentences

**The set.** [`docs/corpus/labelled-sentences.tsv`](corpus/labelled-sentences.tsv)
— 800 rows plus a header, the complete labelled evaluation set:

| column | meaning |
|---|---|
| `index` | the sentence's stable index, used by the scoring scripts |
| `batch` | `pilot`, or `expansion_part0` / `1` / `2` |
| `corpus` | `ietf` or `us-congress` |
| `source_document` | the document the sentence was drawn from, joinable to `documents.tsv` |
| `label` | `YES`, `NO`, or `FRAG` |
| `second_label` | the independent re-label, present for the 200 rows of `expansion_part1` |
| `sentence` | the sentence as the labeller saw it |

**Sampling rule.** Sentences were drawn uniformly at random from a population
defined without reference to this tool's rules: any sentence in the corpus
containing a marker from a fixed list of ordinary English future and obligation
words (`will`, `shall`, `going to`, `agreed to`, `volunteered to`, `committed
to`, `should`, `needs to`, `plans to`, `intends to`, `action item`, `i'll`,
`we'll`, `let me`, `i can`, `by <weekday>`, and similar). The list is a property
of English, not of `cues.py`, which is what makes the sample a fair test rather
than a self-selected one.

**Label definitions,** as given to every labeller:

- `YES` — the sentence commits an identifiable party (person, group or
  organisation) to a specific future action that could later be marked done or
  not done.
- `NO` — everything else: opinions, predictions, questions asking for
  information, descriptions of the past, abstract "should" statements,
  procedural narration of the present moment, hypotheticals committing nobody,
  refusals and negations.
- `FRAG` — cut off exactly where the commitment would be stated, so it cannot
  fairly be judged.

Fifteen worked rulings accompanied the definitions and are reproduced in the
labelling prompt; the four that do most of the work are that "I will now
recognise the gentleman" is procedural narration (NO), "China will continue to
expand its fleet" is a prediction about a party nobody in the room controls
(NO), "Could you send me the spreadsheet afterwards?" is a request for a future
action (YES), and "If we get consensus, I'll write it up" is conditional but a
named party accepts the work (YES).

**What came out.** 81 `YES`, 711 `NO`, 8 `FRAG`. Positive rates across the four
labelling dispatches were 7.5%, 12.5%, 11% and 9.5%.

**Sentences are cut mid-line, on purpose.** Both corpora are hard-wrapped at
about seventy columns, so many sampled sentences are fragments. This is what the
tool sees too, and the README says so.

**Licence.** Public-record text: US Government works are in the public domain,
IETF minutes are IETF Trust proceedings material. The sentences are short
excerpts, republished here because a label set without its text cannot be
checked.

## 3. Which figure came from which pass

The README's results table is not one measurement. It is four, over four
different populations. This is the mapping.

| README row | v0.1 | v0.2 | measured over |
|---|---|---|---|
| precision, 800 blind labels | 0.131 | 0.348 | the 800 above, minus the 8 `FRAG` rows, so **792 scored** |
| recall, 800 blind labels | 0.432 | 0.605 | same 792 |
| recall, whole pipeline over whole documents | 0.318 | 0.455 | **423 documents** — those the labelled sentences came from, run end to end |
| action items the scribes marked and it missed | 1,598 of 1,760 | 1,249 of 1,760 | **all 6,320 documents** |
| findings quoted cut off mid-sentence | 62.6% | 11.7% | a **900-document** random sample; 12,801 findings v0.1, 8,140 v0.2 |
| findings carrying a deadline | 1.5% | 3.7% | the same 900-document sample |
| hard-wrapped files correctly detected as wrapped | 24% | 84% | a **932-document** subset, defined below |
| total findings over the corpus | 90,529 | 63,540 | **all 6,320 documents** |

Supporting figures in the surrounding prose, and where they sit:

- "31,599 findings … from that alone", now 96 — all 6,320 documents.
- "more than a third of everything the tool reported" — 31,599 of 90,529 is
  34.9%.
- "71% of what human scribes wrote down … is still missed" — 1,249 of 1,760,
  all 6,320 documents. The v0.1 rate was 90.8%.
- "6,320 documents, zero crashes, zero timeouts, about a seventh of a second
  each" — all 6,320 documents.
- Owners "According, Deferring and Due — 5.5% of all findings, now 1.8%" — all
  6,320 documents.

**The wrap-detection population, exactly.** The first 2,500 documents of the
frozen corpus list were tested geometrically for hard wrapping, independently of
`wrap_column`: a document counts as looking hard-wrapped if it has at least 40
non-blank lines, its 90th-percentile line length is between 50 and 85
characters, and at least 35% of its lines fall within 10 characters of that
percentile. **932 documents met that test.** `wrap_column` returned a column for
781 of them and nothing for 151 — a detection rate of **83.8%**, which the
README rounds to 84%. The 24% is the same probe against the v0.1 tree.

**The 197-of-200 agreement figure.** The re-label covers `expansion_part1` only,
so the agreement statistic describes 200 of the 800, not all of them. Two views
of the same 200 exist and the README quotes the second: three-way agreement
(`YES`/`NO`/`FRAG`) is 196 of 200 with kappa 0.894; binary agreement (`YES`
versus not-`YES`, which is what precision and recall actually use) is **197 of
200 with kappa 0.919**, which the README rounds to 0.92. Both are recoverable
from the `label` and `second_label` columns.

## 4. What a third party can and cannot reproduce

| claim | status |
|---|---|
| which 6,320 documents | **reproducible** — names, URLs and hashes ship here |
| the IETF selection rule | **reproducible** — stated exactly |
| the congressional selection rule | reproducible as a *procedure*; the exact 587 are pinned by the manifest, not by re-running the seed |
| the 800 labelled sentences and their labels | **reproducible** — the complete set ships here |
| precision, recall and kappa | **reproducible** — recomputable from the label set |
| that the labels are a fair ground truth | **not established** — the labellers were LLM subagents, see the warning at the top |
| the whole-pipeline, truncation and wrap figures | populations named above; the per-run result files are working files on one machine and are **not published** |
| the measurement scripts | **not published** — `tests/test_corpus_defects.py` holds the regression tests the corpus produced, but not the harness that produced the table |
