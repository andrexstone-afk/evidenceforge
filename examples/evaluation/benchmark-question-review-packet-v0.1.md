---
artifact_type: benchmark-question-review-packet
schema_version: "1.0"
dataset_name: "EvidenceForge cross-domain benchmark starter"
dataset_version: "0.1"
review_status: draft
review_scope: question_selection_only
annotation_status: no_gold_labels
versioned_at: 2026-07-29
---

# EvidenceForge benchmark question-selection review packet

> **DRAFT — NOT PHYSICIAN REVIEWED.** This worksheet covers question selection
> only. It contains no gold annotations and makes no clinical-performance claim.

## Review instructions

For each candidate, mark exactly one decision: Include as written, Revise, or
Exclude. If revision is needed, record population-level wording only.

- Do not enter patient-identifiable information.
- Do not assign evidence-relevance or evidence-density labels.
- Do not add ontology gold codes, claim-support labels, or treatment conclusions.
- Do not change the source JSON review status during this worksheet review.
- After all questions are reviewed, record the review date and reviewer count in
  the versioned question-set JSON through the validated EvidenceForge contract.

## Dataset context

- Dataset: EvidenceForge cross-domain benchmark starter
- Version: `0.1`
- Candidate questions: 3
- Review method: Unreviewed starter set assembled from existing service-verified terminology examples for physician scope review.

### Current limitations

- Question selection has not been physician reviewed.
- The set contains no gold PICO, terminology, retrieval, claim-support, or numeric-consistency labels.
- Evidence density remains unknown until retrieval and review.
- Three starter questions do not satisfy the planned 15 to 30 question benchmark.

## 1. ophthalmology — drug comparison

- Case ID: `ophthalmology-amd-drug-comparison`
- Coded artifact: `examples/ophthalmology/amd-coded-brief.md`
- Evidence-density expectation: `unknown`

### Candidate question

> In adults with neovascular age-related macular degeneration, how does aflibercept compare with ranibizumab for improving visual acuity?

### Review focus

- Confirm whether laterality, lesion activity, prior-treatment status, treatment regimen, and time horizon should be specified.

### Decision

- [ ] Include as written
- [ ] Revise
- [ ] Exclude

**Proposed population-level revision (leave blank unless Revise is marked):**

_Reviewer entry:_

**Selection rationale:**

_Reviewer entry:_

## 2. cardiometabolic — drug comparison

- Case ID: `cardiometabolic-type2-diabetes-drug-comparison`
- Coded artifact: `examples/cardiometabolic/type2-diabetes-coded-brief.md`
- Evidence-density expectation: `unknown`

### Candidate question

> In adults with type 2 diabetes mellitus without complications, how does semaglutide compare with empagliflozin for reducing glycated hemoglobin (HbA1c)?

### Review focus

- Confirm whether dose, formulation, background glucose-lowering therapy, and time horizon should be specified.

### Decision

- [ ] Include as written
- [ ] Revise
- [ ] Exclude

**Proposed population-level revision (leave blank unless Revise is marked):**

_Reviewer entry:_

**Selection rationale:**

_Reviewer entry:_

## 3. rare disease — drug comparison

- Case ID: `rare-disease-myasthenia-gravis-drug-comparison`
- Coded artifact: `examples/rare_disease/myasthenia-gravis-coded-brief.md`
- Evidence-density expectation: `unknown`

### Candidate question

> In adults with myasthenia gravis without acute exacerbation, how does efgartigimod alfa compare with rozanolixizumab for improving activities of daily living?

### Review focus

- Confirm whether antibody status, baseline disease severity, dose, background therapy, and time horizon should be specified.

### Decision

- [ ] Include as written
- [ ] Revise
- [ ] Exclude

**Proposed population-level revision (leave blank unless Revise is marked):**

_Reviewer entry:_

**Selection rationale:**

_Reviewer entry:_

## Review completion

- [ ] Every candidate has exactly one decision.
- [ ] Revisions contain population-level wording and no PHI.
- [ ] No gold annotations or clinical conclusions were added.
- Review date (YYYY-MM-DD):
- Reviewer count:
- Reviewer role(s), without personal identifiers:

Completion of this worksheet does not itself change repository provenance.
The versioned question-set JSON must be updated and independently validated.
