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
traceable to retrieved evidence. Model-generated
synthesis, inference, uncertainty, conflicting evidence, and missing evidence must be
distinguished explicitly. High-severity QA findings will block an automatic pass.
