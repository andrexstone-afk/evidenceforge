"""Network-isolated HTML-to-PDF rendering for reviewed briefs."""

from html import escape
from typing import Protocol, cast

from evidenceforge.exporters.models import BriefExportDocument
from evidenceforge.models.evidence import ClinicalTrialRecord, PubMedRecord
from evidenceforge.models.ontology import Mapping
from evidenceforge.ranking.evidence import RankedEvidence


class PDFExportError(RuntimeError):
    """Raised when the configured PDF renderer cannot produce a document."""


class PDFBackend(Protocol):
    """Replaceable HTML-to-PDF boundary."""

    def render(self, html: str) -> bytes: ...


class WeasyPrintBackend:
    """Render self-contained HTML without permitting resource fetches."""

    def render(self, html: str) -> bytes:
        try:
            from weasyprint import HTML  # type: ignore[import-untyped]
        except (ImportError, OSError) as error:
            raise PDFExportError(
                "WeasyPrint is unavailable; install its documented Pango runtime dependencies"
            ) from error

        try:
            result = cast(
                bytes,
                HTML(string=html, url_fetcher=_reject_resource_fetch).write_pdf(),
            )
        except Exception as error:
            raise PDFExportError("PDF rendering failed") from error
        if not result.startswith(b"%PDF-"):
            raise PDFExportError("PDF renderer returned an invalid document")
        return result


def render_export_pdf(
    document: BriefExportDocument,
    *,
    backend: PDFBackend | None = None,
) -> bytes:
    """Render a reviewed brief through an injectable PDF backend."""

    result = (backend or WeasyPrintBackend()).render(render_export_html(document))
    if not result.startswith(b"%PDF-"):
        raise PDFExportError("PDF renderer returned an invalid document")
    return result


def render_export_html(document: BriefExportDocument) -> str:
    """Render self-contained, escaped HTML suitable for deterministic PDF layout."""

    aggregate = document.aggregate
    result = aggregate.synthesis_qa
    draft = result.final_draft
    status_class = "status-pass" if result.final_qa.status.value == "pass" else "status-alert"
    claims = "".join(
        (
            '<section class="claim">'
            f"<h3>{escape(claim.claim_id)} - {escape(claim.claim_type.value)}</h3>"
            f"<p>{escape(claim.text)}</p>"
            f'<p class="meta">Sources: {escape(", ".join(claim.linked_source_ids) or "None")}</p>'
            + "".join(
                (
                    "<blockquote>"
                    f"<strong>{escape(passage.source_id)}</strong>"
                    f"{' - ' + escape(passage.location) if passage.location else ''}: "
                    f"{escape(passage.text)}"
                    "</blockquote>"
                )
                for passage in claim.supporting_passages
            )
            + "</section>"
        )
        for claim in draft.claims
    )
    mappings = "".join(
        (
            "<tr>"
            f"<td>{escape(mapping.original_term)}</td>"
            f"<td>{escape(mapping.ontology.value)}</td>"
            f"<td>{_selected_mapping_html(mapping)}</td>"
            f"<td>{'Yes' if mapping.human_review_required else 'No'}</td>"
            "</tr>"
        )
        for mapping in aggregate.mappings
    )
    ranking = {item.record_id: item for item in aggregate.retrieval.ranking}
    evidence_rows = "".join(
        _evidence_row_html("PubMed", record, ranking.get(record.record_id))
        for record in aggregate.retrieval.pubmed.records
    ) + "".join(
        _evidence_row_html("ClinicalTrials.gov", record, ranking.get(record.record_id))
        for record in aggregate.retrieval.clinical_trials.records
    )
    assessment_rows = "".join(
        (
            "<tr>"
            f"<td>{escape(item.claim_id)}</td>"
            f"<td>{escape(item.classification.value)}</td>"
            f"<td>{escape(item.severity.value)}</td>"
            f"<td>{escape(item.explanation)}</td>"
            "</tr>"
        )
        for item in result.final_qa.assessments
    )
    deterministic_rows = "".join(
        (
            "<tr>"
            f"<td>{escape(item.claim_id)}</td>"
            f"<td>{escape(item.rule.value)}</td>"
            f"<td>{escape(item.severity.value)}</td>"
            f"<td>{escape(item.message)}</td>"
            "</tr>"
        )
        for item in result.final_qa.deterministic_findings
    )
    qa_rows = assessment_rows + deterministic_rows
    revisions = (
        "<p>No revision was required.</p>"
        if result.revision is None
        else "<ul>"
        + "".join(
            f"<li><strong>{escape(change.claim_id)}</strong>: {escape(change.reason)}</li>"
            for change in result.revision.changes
        )
        + "</ul>"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>EvidenceForge brief {escape(document.metatags.brief_id)}</title>
<style>
@page {{
  size: Letter;
  margin: 0.65in 0.7in 0.7in;
  @bottom-right {{ content: "Page " counter(page) " of " counter(pages); color: #64748b; }}
}}
body {{ font-family: Arial, sans-serif; color: #172033; font-size: 9.2pt; line-height: 1.35; }}
h1 {{ color: #143d59; font-size: 19pt; line-height: 1.25; margin: 0 0 6pt; }}
h2 {{ color: #176b87; font-size: 13pt; margin: 13pt 0 5pt; border-bottom: 1px solid #b6d8e4; }}
h3 {{ color: #143d59; font-size: 10pt; margin: 0 0 4pt; }}
p {{ margin: 3pt 0 6pt; }}
.eyebrow {{ color: #176b87; font-size: 8pt; font-weight: bold; letter-spacing: 0.08em; }}
.status {{ display: inline-block; padding: 3pt 7pt; border-radius: 10pt; font-weight: bold; }}
.status-pass {{ background: #e8f5ef; color: #176b4b; }}
.status-alert {{ background: #fee2e2; color: #991b1b; }}
.warning {{ border-left: 4px solid #d97706; background: #fff7e8; padding: 6pt 8pt; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6pt 16pt; }}
.label {{ color: #64748b; font-size: 8pt; text-transform: uppercase; }}
.claim {{ border: 1px solid #d7e4ea; border-radius: 5pt; padding: 6pt 8pt; margin: 0 0 6pt;
  break-inside: avoid; }}
.meta {{ color: #475569; font-size: 8.5pt; }}
blockquote {{ margin: 4pt 0 0; padding: 5pt 7pt; background: #f5f8fa; color: #334155; }}
table {{ width: 100%; border-collapse: collapse; font-size: 8.5pt; }}
th {{ background: #143d59; color: white; text-align: left; padding: 4pt; }}
td {{ border: 1px solid #d7e4ea; padding: 4pt; vertical-align: top; }}
ul {{ margin-top: 4pt; padding-left: 16pt; }}
.footer-note {{ margin-top: 18pt; color: #64748b; font-size: 8pt; }}
</style>
</head>
<body>
<div class="eyebrow">EVIDENCEFORGE - REVIEWED EVIDENCE BRIEF</div>
<h1>{escape(aggregate.question)}</h1>
<p><span class="status {status_class}">QA: {escape(result.final_qa.status.value)}</span></p>
<p class="warning">{escape(result.disclaimer)}</p>

<h2>Parsed PICO</h2>
<div class="grid">
<div><div class="label">Population</div>{escape(aggregate.pico.population)}</div>
<div><div class="label">Condition</div>{escape(aggregate.pico.condition)}</div>
<div><div class="label">Intervention</div>{escape(aggregate.pico.intervention)}</div>
<div><div class="label">Comparator</div>{escape(aggregate.pico.comparator)}</div>
<div><div class="label">Outcomes</div>{escape(", ".join(aggregate.pico.outcomes))}</div>
<div><div class="label">Time horizon</div>
{escape(aggregate.pico.time_horizon or "Not specified")}</div>
</div>

<h2>Executive answer</h2>
<p>{escape(draft.executive_answer)}</p>
<h2>Evidence summary</h2>
<p>{escape(draft.evidence_summary)}</p>
<h2>Claims and supporting passages</h2>
{claims}

<h2>Retrieved evidence</h2>
<table><thead><tr><th>ID</th><th>Source and title</th><th>Ranking</th></tr></thead>
<tbody>{evidence_rows or '<tr><td colspan="3">No evidence records retained.</td></tr>'}</tbody>
</table>

<h2>Terminology mappings</h2>
<table><thead><tr><th>Term</th><th>Ontology</th><th>Selected code</th><th>Review</th></tr></thead>
<tbody>{mappings or '<tr><td colspan="4">No mappings retained.</td></tr>'}</tbody></table>

<h2>Clinical interpretation</h2>
<p>{escape(draft.clinical_interpretation)}</p>
<h2>Limitations, uncertainty, and gaps</h2>
{_html_list("Limitations", draft.limitations)}
{_html_list("Uncertainties", draft.uncertainties)}
{_html_list("Evidence gaps", draft.evidence_gaps)}

<h2>Final claim-level QA</h2>
<table><thead><tr><th>Claim</th><th>Classification</th><th>Severity</th><th>Explanation</th></tr></thead>
<tbody>{qa_rows or '<tr><td colspan="4">No final assessments retained.</td></tr>'}</tbody></table>

<h2>Revision history</h2>
{revisions}
<p class="footer-note">Brief ID: {escape(document.metatags.brief_id)} |
Generated: {escape(aggregate.created_at.isoformat())} |
Export schema: {escape(document.schema_version)}</p>
</body>
</html>"""


def _selected_mapping_html(mapping: Mapping) -> str:
    selected = mapping.selected
    if selected is None:
        return "No validated selection"
    return f"<code>{escape(selected.code)}</code> - {escape(selected.preferred_label)}"


def _html_list(title: str, values: tuple[str, ...]) -> str:
    items = "".join(f"<li>{escape(value)}</li>" for value in values) or "<li>None recorded.</li>"
    return f"<h3>{escape(title)}</h3><ul>{items}</ul>"


def _evidence_row_html(
    source: str,
    record: PubMedRecord | ClinicalTrialRecord,
    ranked: RankedEvidence | None,
) -> str:
    record_id = escape(record.record_id)
    title = escape(record.title)
    url = escape(record.url)
    if ranked is None:
        ranking = "Not ranked"
    else:
        ranking = f'{ranked.score:.3f}<br><span class="meta">{escape(ranked.method)}</span>'
    return (
        "<tr>"
        f"<td><code>{record_id}</code></td>"
        f"<td><strong>{escape(source)}</strong><br>{title}<br>"
        f'<span class="meta">{url}</span></td>'
        f"<td>{ranking}</td>"
        "</tr>"
    )


def _reject_resource_fetch(url: str, *args: object, **kwargs: object) -> dict[str, object]:
    del args, kwargs
    raise PDFExportError(f"External PDF resource fetch blocked: {url}")
