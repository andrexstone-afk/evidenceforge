# Rare-disease evidence-retrieval checkpoint

Verified: 2026-07-30

## Scope

This checkpoint verifies reproducible search construction and source identities for the
existing myasthenia gravis question. It is not a clinical evidence synthesis, relevance
adjudication, treatment comparison, proof of evidence absence, or benchmark gold label.

## Clinical question

In adults with myasthenia gravis without acute exacerbation, how does efgartigimod alfa
compare with rozanolixizumab for improving activities of daily living?

## Search strategy

The ICD-10-CM and RxNorm labels remain unchanged in the coded brief. Evidence search
uses explicit, human-inspectable overrides:

- condition term: `myasthenia gravis`
- intervention term: `efgartigimod`
- comparator term: `rozanolixizumab`
- outcome term: `MG-ADL`
- trial scope: either named intervention, so both independent development programs can
  be inspected

No automatic rule removes “without acute exacerbation” or “alfa.” The evidence terms
are passed deliberately so the exact search remains visible in source metadata.

### PubMed

```text
"myasthenia gravis"[Title/Abstract] AND "efgartigimod"[Title/Abstract] AND "rozanolixizumab"[Title/Abstract] AND ("MG-ADL"[Title/Abstract])
```

### ClinicalTrials.gov API v2

```text
"myasthenia gravis" AND ("efgartigimod" OR "rozanolixizumab")
```

## Source verification

The ClinicalTrials.gov broad query above was executed through EvidenceForge's
allowlisted v2 client on 2026-07-30 with a page size of 20. The service reported 43
records, and the first page included both
[NCT03669588](https://clinicaltrials.gov/study/NCT03669588) and
[NCT03971422](https://clinicaltrials.gov/study/NCT03971422). Counts and ordering are
dynamic and must be retained with each execution timestamp.

The corresponding field-scoped query requiring both interventions was also executed:

```text
AREA[ConditionSearch]"myasthenia gravis" AND AREA[InterventionName]"efgartigimod" AND AREA[InterventionName]"rozanolixizumab"
```

It returned zero records at that time. A zero search result is query- and
time-dependent; it does not prove that no direct comparative evidence exists.

The PubMed client was **not** executed because no NCBI maintainer email was configured.
EvidenceForge does not substitute a fake contact address. Official PubMed pages were
inspected to verify candidate source identities:

- [PMID 38431900](https://pubmed.ncbi.nlm.nih.gov/38431900/)
- [PMID 40257679](https://pubmed.ncbi.nlm.nih.gov/40257679/)

This checkpoint does not label either record relevant, quote or redistribute either
abstract, or use source contents to make an efficacy or safety claim. Credentialed
PubMed retrieval and independent relevance review remain pending.

## Deterministic test coverage

Default tests use clearly synthetic PubMed and ClinicalTrials.gov response fixtures.
They verify that the explicit search terms reach both clients, that each client records
the exact query it received, and that separate synthetic trial-program records enter
transparent ranking. Synthetic identifiers and text have no clinical-performance
meaning.
