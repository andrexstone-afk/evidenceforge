---
brief_type: coded-clinical-question
question: In adults with myasthenia gravis without acute exacerbation, how does efgartigimod
  alfa compare with rozanolixizumab for improving activities of daily living?
generated_at: '2026-07-29T16:55:26.862268+00:00'
prompt_version: pico-v1
llm_provider: mock
llm_model: deterministic-rare-disease-fixture-v1
---

# EvidenceForge coded brief

> Research evidence-synthesis prototype; not a medical device, not for diagnosis, and not individualized clinical advice.

## Clinical question

In adults with myasthenia gravis without acute exacerbation, how does efgartigimod alfa compare with rozanolixizumab for improving activities of daily living?

## Parsed PICO

- Population: Adults with myasthenia gravis without acute exacerbation
- Intervention: efgartigimod alfa
- Comparator: rozanolixizumab
- Outcomes: activities of daily living
- Missing information: antibody status, baseline disease severity, time horizon, dose and treatment schedule, background therapy

## Ontology mappings

### myasthenia gravis without acute exacerbation

- Ontology: ICD-10-CM
- Selected: `G70.00` — Myasthenia gravis without (acute) exacerbation
- Match method: exact normalized service-label match
- Human review required: no
- Review note: None
- Source: https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search
- Alternatives:
  - `G70.00` — Myasthenia gravis without (acute) exacerbation

### efgartigimod alfa

- Ontology: RxNorm
- Selected: `2587717` — efgartigimod alfa
- Match method: exact normalized label within RxNorm approximate candidates
- Human review required: no
- Review note: None
- Source: https://rxnav.nlm.nih.gov/REST/approximateTerm.json
- Alternatives:
  - `2587717` — efgartigimod alfa

### rozanolixizumab

- Ontology: RxNorm
- Selected: `2642274` — rozanolixizumab
- Match method: exact normalized label within RxNorm approximate candidates
- Human review required: no
- Review note: None
- Source: https://rxnav.nlm.nih.gov/REST/approximateTerm.json
- Alternatives:
  - `2642274` — rozanolixizumab

## Scope

This Phase 1 artifact structures the question and validates terminology mappings. It does not retrieve or synthesize clinical evidence.

## Generation metadata

- Provider: mock
- Model: deterministic-rare-disease-fixture-v1
- Latency: 1.24 ms
- Input tokens: not reported
- Output tokens: not reported
- Retry count: 0

## Verification and limitations

This artifact was generated on 2026-07-29 through the working coded-brief pipeline
using live, allowlisted NLM Clinical Tables and RxNorm clients. The selected codes above
were returned by those services; they were not generated from model memory.

The question explicitly says “without acute exacerbation.” EvidenceForge does not infer
that state from a generic myasthenia gravis question. Antibody status, baseline disease
severity, dosing and treatment schedules, background therapy, and follow-up duration
remain unspecified. This artifact makes no claim about comparative efficacy, safety, or
appropriate treatment. Evidence retrieval, synthesis, claim-level QA, and physician
review for this question remain future work.
