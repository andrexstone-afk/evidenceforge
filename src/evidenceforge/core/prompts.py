"""Safe loading for versioned prompt files in checkouts and built wheels."""

from importlib.resources import files
from pathlib import Path, PurePosixPath, PureWindowsPath

SOURCE_PROMPTS_PATH = Path(__file__).parents[3] / "prompts"


def load_versioned_prompt(relative_path: str) -> str:
    """Load a prompt while rejecting absolute and parent-traversal paths."""

    path = PurePosixPath(relative_path)
    windows_path = PureWindowsPath(relative_path)
    if (
        path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or ".." in path.parts
        or ".." in windows_path.parts
        or not path.parts
    ):
        raise ValueError("Prompt path must remain inside the prompts directory")
    source_path = SOURCE_PROMPTS_PATH.joinpath(*path.parts)
    if source_path.exists():
        return source_path.read_text(encoding="utf-8")
    return files("evidenceforge").joinpath("prompts", *path.parts).read_text(encoding="utf-8")
