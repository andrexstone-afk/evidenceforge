from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from evidenceforge.exporters import build_export_document, render_export_pdf
from tests.fixtures.persistence import persistence_input

BRIEF_ID = "11111111-2222-4333-8444-555555555555"


async def test_weasyprint_generates_readable_reviewed_brief_pdf(
    monkeypatch,
) -> None:
    homebrew_lib = Path("/opt/homebrew/lib")
    if homebrew_lib.is_dir():
        monkeypatch.setenv("DYLD_FALLBACK_LIBRARY_PATH", str(homebrew_lib))
    document = build_export_document(
        brief_id=BRIEF_ID,
        aggregate=await persistence_input(),
    )

    pdf = render_export_pdf(document)
    reader = PdfReader(BytesIO(pdf))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert len(reader.pages) >= 1
    assert "EVIDENCEFORGE" in text
    assert "QA: pass" in text
    assert "CLM-0001" in text
