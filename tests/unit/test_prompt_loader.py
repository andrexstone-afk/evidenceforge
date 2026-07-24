import pytest

from evidenceforge.core.prompts import load_versioned_prompt


def test_prompt_loader_reads_versioned_phase_three_prompt() -> None:
    prompt = load_versioned_prompt("qa/v1.md")

    assert "untrusted-input envelope" in prompt
    assert "untracked claim" in prompt


@pytest.mark.parametrize(
    "path",
    [
        "../secrets.txt",
        "/tmp/prompt.md",
        r"..\outside.md",
        r"C:\outside.md",
        r"\\server\share\outside.md",
    ],
)
def test_prompt_loader_rejects_paths_outside_prompt_directory(path: str) -> None:
    with pytest.raises(ValueError, match="prompts directory"):
        load_versioned_prompt(path)
