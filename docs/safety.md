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

Reviewed exports do not call terminology, evidence, or LLM services. JSON preserves the
validated aggregate as data. Markdown escapes untrusted clinical and retrieved text in
the rendered body so embedded HTML or image syntax is inert. PDF content is HTML-escaped,
self-contained, and rendered with external resource fetching disabled. The safety
disclaimer and final QA status remain visible in human-readable exports.

Export metadata excludes artifact bytes and user-provided local paths; the latter may
contain identifying information. CLI overwrite handling never replaces directories and
restores a prior file if metadata persistence fails.

The Streamlit interface accepts a persisted brief UUID, not a clinical question or
patient data. Its API origin comes from typed environment configuration and cannot be
changed through the browser. The dedicated client uses bounded timeouts, does not follow
redirects, validates response schemas and export media types, and converts failures to
stable messages without reflecting server response bodies. Retrieved and generated
text is displayed without unsafe HTML. Blocked final QA is presented as an error and is
never styled as passing.
