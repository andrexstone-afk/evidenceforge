# Cardiometabolic evidence-retrieval checkpoint

Verified: 2026-07-30

## Scope

This checkpoint verifies reproducible search construction and source identities for the
existing type 2 diabetes question. It is not a clinical evidence synthesis, relevance
adjudication, treatment comparison, or benchmark gold label.

## Clinical question

In adults with type 2 diabetes mellitus without complications, how does semaglutide
compare with empagliflozin for reducing glycated hemoglobin (HbA1c)?

## Search strategy

The ICD-10-CM-oriented condition label remains unchanged in the coded brief. Evidence
search uses an explicit, human-inspectable override:

- condition term: `type 2 diabetes mellitus`
- outcome term: `HbA1c`
- trial scope: both named interventions must appear in intervention fields

No automatic rule strips “without complications.” The broader evidence term is passed
deliberately so the exact search is visible in the resulting metadata.

### PubMed

```text
"type 2 diabetes mellitus"[Title/Abstract] AND "semaglutide"[Title/Abstract] AND "empagliflozin"[Title/Abstract] AND ("HbA1c"[Title/Abstract])
```

### ClinicalTrials.gov API v2

```text
AREA[ConditionSearch]"type 2 diabetes mellitus" AND AREA[InterventionName]"semaglutide" AND AREA[InterventionName]"empagliflozin"
```

## Source verification

The ClinicalTrials.gov query above was executed through EvidenceForge's allowlisted v2
client on 2026-07-30 with a page size of 10. The service reported 10 records and the
first page included
[NCT02863328](https://clinicaltrials.gov/study/NCT02863328). Counts and ordering are
dynamic and must be retained with each execution timestamp.

The PubMed client was **not** executed because no NCBI maintainer email was configured.
EvidenceForge does not substitute a fake contact address. Official PubMed pages were
inspected to verify candidate source identities:

- [PMID 31530666](https://pubmed.ncbi.nlm.nih.gov/31530666/)
- [PMID 40990044](https://pubmed.ncbi.nlm.nih.gov/40990044/)

This page does not label either record relevant, quote or redistribute either abstract,
or use their contents to make an efficacy or safety claim. Credentialed PubMed
retrieval and independent relevance review remain pending.

## Deterministic test coverage

Default tests use clearly synthetic PubMed and ClinicalTrials.gov response fixtures.
They verify that the explicit strategy reaches both clients, that each client records
the exact query it received, and that normalized records enter transparent ranking.
Synthetic identifiers and text have no clinical-performance meaning.
