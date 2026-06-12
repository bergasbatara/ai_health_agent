from __future__ import annotations

import hashlib
from pathlib import Path

from domain import PayerId

from .models import DiscoveredPdf


PAYER_NAME_MAP: tuple[tuple[str, PayerId], ...] = (
    ("aetna", PayerId.AETNA),
    ("cigna", PayerId.CIGNA),
    ("medadv", PayerId.MEDADV),
)


def infer_payer_id(filename: str) -> PayerId:
    normalized_name = filename.casefold()
    for token, payer_id in PAYER_NAME_MAP:
        if token in normalized_name:
            return payer_id
    return PayerId.OTHER


def compute_file_checksum(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        while chunk := file_handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def discover_pdfs(data_dir: str | Path) -> list[DiscoveredPdf]:
    root = Path(data_dir)
    if not root.exists():
        raise FileNotFoundError(f"Data directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Data path is not a directory: {root}")

    discovered: list[DiscoveredPdf] = []
    for path in sorted(root.rglob("*.pdf"), key=lambda item: item.name.casefold()):
        discovered.append(
            DiscoveredPdf(
                path=path.resolve(),
                filename=path.name,
                payer_id=infer_payer_id(path.name),
                checksum_sha256=compute_file_checksum(path),
            )
        )
    return discovered
