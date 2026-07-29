---
brief_type: coded-clinical-question
question: In adults with type 2 diabetes mellitus without complications, how does
  semaglutide compare with empagliflozin for reducing glycated hemoglobin (HbA1c)?
generated_at: '2026-07-29T16:45:31.991259+00:00'
prompt_version: pico-v1
llm_provider: mock
llm_model: deterministic-cardiometabolic-fixture-v1
---

# EvidenceForge coded brief

> Research evidence-synthesis prototype; not a medical device, not for diagnosis, and not individualized clinical advice.

## Clinical question

In adults with type 2 diabetes mellitus without complications, how does semaglutide compare with empagliflozin for reducing glycated hemoglobin (HbA1c)?

## Parsed PICO

- Population: Adults with type 2 diabetes mellitus without complications
- Intervention: semaglutide
- Comparator: empagliflozin
- Outcomes: glycated hemoglobin (HbA1c)
- Missing information: time horizon, dose and formulation, background glucose-lowering therapy

## Ontology mappings

### type 2 diabetes mellitus without complications

- Ontology: ICD-10-CM
- Selected: `E11.9` — Type 2 diabetes mellitus without complications
- Match method: exact normalized service-label match
- Human review required: no
- Review note: None
- Source: https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search
- Alternatives:
  - `E11.9` — Type 2 diabetes mellitus without complications
  - `E11.A` — Type 2 diabetes mellitus without complications in remission

### semaglutide

- Ontology: RxNorm
- Selected: `1991302` — semaglutide
- Match method: exact normalized label within RxNorm approximate candidates
- Human review required: no
- Review note: None
- Source: https://rxnav.nlm.nih.gov/REST/approximateTerm.json
- Alternatives:
  - `1991302` — semaglutide

### empagliflozin

- Ontology: RxNorm
- Selected: `1545653` — empagliflozin
- Match method: exact normalized label within RxNorm approximate candidates
- Human review required: no
- Review note: None
- Source: https://rxnav.nlm.nih.gov/REST/approximateTerm.json
- Alternatives:
  - `1545653` — empagliflozin

## Scope

This Phase 1 artifact structures the question and validates terminology mappings. It does not retrieve or synthesize clinical evidence.

## Generation metadata

- Provider: mock
- Model: deterministic-cardiometabolic-fixture-v1
- Latency: 1.23 ms
- Input tokens: not reported
- Output tokens: not reported
- Retry count: 0

## Verification and limitations

This artifact was generated on 2026-07-29 through the working coded-brief pipeline
using live, allowlisted NLM Clinical Tables and RxNorm clients. The selected codes and
alternatives above were returned by those services; they were not generated from model
memory.

The question explicitly says “without complications.” EvidenceForge does not infer
that clinical status from a generic type 2 diabetes question. This artifact makes no
claim about comparative efficacy, safety, dose, formulation, follow-up duration, or
appropriate treatment. Evidence retrieval, synthesis, claim-level QA, and physician
review for this cardiometabolic question remain future work.
