---
brief_type: coded-clinical-question
question: "In adults with neovascular age-related macular degeneration, how does aflibercept compare with ranibizumab for improving visual acuity?"
generated_at: 2026-07-24T20:50:07.884216+00:00
prompt_version: pico-v1
llm_provider: mock
llm_model: deterministic-amd-fixture-v1
---

# EvidenceForge coded brief

> Research evidence-synthesis prototype; not a medical device, not for diagnosis, and not individualized clinical advice.

## Clinical question

In adults with neovascular age-related macular degeneration, how does aflibercept compare with ranibizumab for improving visual acuity?

## Parsed PICO

- Population: Adults with neovascular age-related macular degeneration
- Intervention: aflibercept
- Comparator: ranibizumab
- Outcomes: visual acuity
- Missing information: time horizon, eye laterality

## Ontology mappings

### neovascular age-related macular degeneration

- Ontology: ICD-10-CM
- Selected: `H35.3291` — Exudative age-related macular degeneration, unspecified eye, with active choroidal neovascularization
- Match method: deterministic laterality-and-activity ranking
- Human review required: yes
- Review note: Confirm provisional mapping because the question omits eye laterality, lesion activity.
- Source: https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search
- Alternatives:
  - `H35.3211` — Exudative age-related macular degeneration, right eye, with active choroidal neovascularization
  - `H35.3212` — Exudative age-related macular degeneration, right eye, with inactive choroidal neovascularization
  - `H35.3221` — Exudative age-related macular degeneration, left eye, with active choroidal neovascularization

### aflibercept

- Ontology: RxNorm
- Selected: `1232150` — aflibercept
- Match method: exact normalized label within RxNorm approximate candidates
- Human review required: no
- Review note: None
- Source: https://rxnav.nlm.nih.gov/REST/approximateTerm.json
- Alternatives:
  - `1232150` — aflibercept

### ranibizumab

- Ontology: RxNorm
- Selected: `595060` — ranibizumab
- Match method: exact normalized label within RxNorm approximate candidates
- Human review required: no
- Review note: None
- Source: https://rxnav.nlm.nih.gov/REST/approximateTerm.json
- Alternatives:
  - `595060` — ranibizumab

## Scope

This Phase 1 artifact structures the question and validates terminology mappings. It does not retrieve or synthesize clinical evidence.

## Generation metadata

- Provider: mock
- Model: deterministic-amd-fixture-v1
- Latency: 0.25 ms
- Input tokens: not reported
- Output tokens: not reported
- Retry count: 0
