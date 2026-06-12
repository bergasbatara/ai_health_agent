from __future__ import annotations

from pathlib import Path

from .models import RawCaseFile


SUPPORTED_CASE_EXTENSIONS = {
    ".json": "json",
    ".txt": "text",
    ".md": "text",
}


def infer_case_file_format(path: str | Path) -> str:
    suffix = Path(path).suffix.casefold()
    try:
        return SUPPORTED_CASE_EXTENSIONS[suffix]
    except KeyError as exc:
        raise ValueError(f"Unsupported case file extension: {suffix or '<none>'}") from exc


def load_case_file(path: str | Path) -> RawCaseFile:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Case file does not exist: {file_path}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Case path is not a file: {file_path}")

    content = file_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Case file is empty: {file_path}")

    return RawCaseFile(
        path=file_path.resolve(),
        filename=file_path.name,
        file_format=infer_case_file_format(file_path),
        content=content,
    )


def discover_case_files(data_dir: str | Path) -> list[RawCaseFile]:
    root = Path(data_dir)
    if not root.exists():
        raise FileNotFoundError(f"Case directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Case path is not a directory: {root}")

    case_files: list[RawCaseFile] = []
    supported_suffixes = set(SUPPORTED_CASE_EXTENSIONS)
    for path in sorted(root.rglob("*"), key=lambda item: item.name.casefold()):
        if not path.is_file():
            continue
        if path.suffix.casefold() not in supported_suffixes:
            continue
        case_files.append(load_case_file(path))
    return case_files
