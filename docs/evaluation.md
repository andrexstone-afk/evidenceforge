# Evaluation design

Phase 6 introduces a deterministic evaluation contract before adding a clinical
benchmark. The current repository can validate aligned evaluation inputs and calculate
auditable metrics, but it does **not** yet contain physician-reviewed gold labels or
support any claim of clinical performance.

## Why the contract comes first

An evaluation result is meaningful only when the reference annotations, system output,
review method, scoring definition, dataset size, and limitations remain together.
EvidenceForge therefore scores one immutable `EvaluationRun` and emits an
`EvaluationReport` that preserves:

- version `1.0` input, report, and scoring contracts;
- dataset name, version, review status, review method, reviewer count, and review date;
- system, model, and prompt versions;
- run timestamp, scoring/tool versions, and a SHA-256 digest of the complete input;
- cost-estimation basis and explicit limitations;
- numerator, denominator, value, and definition for every ratio.

The input schema distinguishes `draft`, `synthetic_test`, and `physician_reviewed`.
`physician_reviewed` requires at least one reviewer and a review date. This label
describes annotation provenance only; it does not imply that the dataset is complete,
publishable, clinically validated, or suitable for a medical-device claim.

## Draft question-selection contract

The versioned
[`benchmark-question-set-v0.1.json`](../examples/evaluation/benchmark-question-set-v0.1.json)
is a physician-review handoff, not an `EvaluationRun`. It contains only the three
existing population-level example questions, links to their terminology-coded
artifacts, and scope questions for a reviewer. Its contract enforces:

- `review_scope: question_selection_only`;
- `annotation_status: no_gold_labels`;
- draft provenance with zero reviewers and no review date;
- `evidence_density_expectation: unknown` for every question;
- unique case IDs and questions, PHI screening, and repository-relative artifact paths.

Changing the question-set status to `physician_reviewed` requires a reviewer count and
review date, but still certifies only question selection. It does not convert the file
into gold PICO, terminology, retrieval, or claim-support annotations, and the scoring
command does not accept it. The starter's three questions are deliberately below the
planned 15–30 case benchmark.

## Aligned case contract

Each case contains a de-identified population-level question and:

1. reviewer-authored PICO reference components and the predicted PICO;
2. aligned terminology entities with expected/predicted normalized terms,
   reviewer-accepted service codes, and ranked service-returned codes;
3. reviewer-relevant evidence identifiers and ranked retrieved identifiers;
4. system and reviewer support classifications for aligned claims, claim citations,
   and an optional reviewer numeric-consistency judgment;
5. end-to-end latency and an estimated cost with a run-level cost basis.

Mapping references must come from the configured terminology services. Evidence
identifiers must be PubMed PMIDs or ClinicalTrials.gov NCT IDs. The schema validates
identifier shape and uniqueness but cannot prove that a reviewer annotation is
clinically correct; that remains a human governance responsibility.

Evaluation JSON is also screened for high-signal patient identifiers at the CLI
boundary. This is defense in depth, not a substitute for de-identification.

## Metric definitions

| Metric | Definition |
|---|---|
| PICO component accuracy | Exact case-insensitive, whitespace-normalized agreement across population, condition, intervention, comparator, outcome set, time horizon, and study context |
| Entity-normalization accuracy | Exact normalized-term agreement for each aligned terminology entity |
| Top-1 mapping accuracy | Fraction of aligned mappings whose first predicted code is reviewer accepted |
| Top-3 mapping recall | Fraction of aligned mappings with any accepted code among the first three predictions |
| Retrieval precision@k | Micro-averaged relevant records among up to the first `k` retrieved records per case |
| Citation validity | Fraction of claim citation identifiers present in that case's retrieved evidence set |
| Claim-support precision | Among claims the system calls supported or partially supported, the fraction independently classified likewise |
| Unsupported-claim rate | Fraction of aligned claims independently classified unsupported, contradicted, or unable to verify |
| Numeric consistency | Fraction of reviewer-assessed numeric claims marked contextually consistent |
| Latency | Arithmetic mean and nearest-rank p95 end-to-end milliseconds per brief |
| Estimated cost | Arithmetic mean estimated USD per brief under the preserved cost basis |

Text matching is intentionally conservative. It normalizes case and repeated whitespace
but does not use fuzzy matching, embeddings, or an LLM. Outcome order does not matter,
but duplicate outcomes are retained as extraction errors. Retrieval precision is
micro-averaged, so every returned record contributes equally.

When a metric has no eligible observations, its JSON `value` is `null` and its
denominator is zero. Undefined metrics are never silently converted to zero.

## Running the scorer

The scorer performs no network or model calls:

```bash
uv run evidenceforge evaluation schema > evaluation-schemas.json
uv run evidenceforge evaluation score \
  --input evaluation-run.json \
  --output evaluation-report.json
```

Existing reports are preserved unless `--force` is supplied. Inputs over 10 MiB are
rejected to keep the local boundary predictable. Invalid schemas, non-UTF-8 input, PHI
screen findings, and filesystem errors are returned as stable CLI errors without
tracebacks.

The report's `input_sha256` binds the metrics to the exact canonicalized validated
input. `generated_at` records when the report was produced, so two reports may have
different generation timestamps while retaining the same input digest and metric
values.

The schema command emits separate `benchmark_question_set`, `evaluation_run`, and
`evaluation_report` schemas so a question-selection handoff cannot be mistaken for a
scorable run.

## Benchmark authoring workflow

The remaining Phase 6 benchmark should contain approximately 15–30 questions spanning:

- ophthalmology;
- cardiology/endocrinology;
- rare disease and sparse evidence;
- drug comparisons, procedures, and diagnostics;
- incomplete PICO and low-evidence cases.

Before reporting results:

1. freeze a versioned question set and annotation guide;
2. retrieve terminology and evidence references from the official services;
3. record reviewer roles, review dates, adjudication method, and limitations;
4. run the configured pipeline without changing gold labels;
5. align variable generated claims for independent support review;
6. preserve model, prompt, latency, token/cost, and run metadata;
7. score the frozen run and review outliers before publishing any summary.

Every reported metric must state dataset size, review method, scoring definition, and
known limitations. Synthetic fixtures exercise arithmetic only and must never appear in
a clinical-performance table.

## Current limitations

- Cardiometabolic and rare-disease terminology-coded seeds and reproducible retrieval
  strategy checkpoints are committed, but no reviewed cross-domain evidence sets, QA
  outputs, or benchmark labels are committed yet.
- No benchmark case has been labeled `physician_reviewed`.
- Claim alignment and clinical adjudication remain human-authored inputs.
- Citation validity confirms membership in the retrieved set; claim-support precision
  separately captures whether the citation supports the claim.
- Cost is an estimate supplied with an explicit basis, not a billing record.
- The metrics characterize one frozen dataset and do not establish generalization,
  clinical utility, or safety.
