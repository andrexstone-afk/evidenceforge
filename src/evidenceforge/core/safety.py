"""Shared boundary checks for prohibited patient-identifiable input."""

import re


class UnsafeClinicalQuestionError(ValueError):
    """Raised when no-PHI confirmation or screening fails."""


def validate_population_question(question: str, *, confirmed_no_phi: bool) -> str:
    """Validate and screen a population-level question before processing or storage."""

    cleaned = question.strip()
    if len(cleaned) < 10:
        raise UnsafeClinicalQuestionError("Clinical question must contain at least 10 characters")
    if not confirmed_no_phi:
        raise UnsafeClinicalQuestionError(
            "Confirm that the question contains no PHI before processing."
        )
    if looks_like_phi(cleaned):
        raise UnsafeClinicalQuestionError(
            "Question appears to contain patient-identifiable information; "
            "use a de-identified population-level question."
        )
    return cleaned


def validate_no_phi_artifact(serialized_artifact: str) -> None:
    """Reject high-signal identifiers anywhere in a submitted artifact."""

    if looks_like_phi(serialized_artifact):
        raise UnsafeClinicalQuestionError(
            "Artifact appears to contain patient-identifiable information; "
            "submit only de-identified population-level content."
        )


def looks_like_phi(text: str) -> bool:
    """Return whether limited high-signal identifier patterns are present."""

    patterns = (
        r"\bMRN\s*[:#-]?\s*\d{4,}\b",
        r"\b(?:date of birth|DOB)\s*[:#-]",
        (
            r"\b(?:date of birth|DOB)\s+"
            r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"
        ),
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
    )
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)
