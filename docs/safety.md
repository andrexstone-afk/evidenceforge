# Clinical safety

EvidenceForge is a research and evidence-synthesis prototype. It is not a medical
device, not for diagnosis, not a substitute for clinical judgment, and not a source of
individualized treatment recommendations.

The project prohibits PHI input. The CLI requires an explicit no-PHI declaration and
screens for common identifier patterns before external calls, but automated screening
cannot guarantee de-identification. Users must provide population-level questions only.
OpenAI Responses requests explicitly disable server-side response storage with
`store=false`; this does not make PHI input permissible.

Ontology codes must come from terminology services, and medical claims must remain
traceable to retrieved evidence. Model-generated synthesis, inference, uncertainty,
conflicting evidence, and missing evidence must be distinguished explicitly.

Retrieved text and generated drafts are treated as untrusted prompt data. The
claim-level QA service requires retrieved source IDs and source-preserving passages,
checks reviewer citations against normalized evidence, and combines independent review
with deterministic numeric, study-design, trial-status, outcome-role, and causal-language
checks. Status is derived in code. High-severity explicit-claim or untracked-narrative
findings block automatic passage, including after revision.

These controls detect defined consistency failures; they do not clinically validate a
brief or replace expert assessment. Current QA fixtures are synthetic.
