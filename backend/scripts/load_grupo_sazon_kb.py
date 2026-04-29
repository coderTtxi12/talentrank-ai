"""Load Grupo Sazon public info into Chroma.

Reads `backend/docs/GRUPO_SAZON_PUBLIC_INFO_ES.txt`, splits it into
section-aware chunks (each section title + its bullets is one chunk),
and upserts to the configured Chroma collection using OpenAI ada
embeddings.

Run from the `backend/` directory:

    python scripts/load_grupo_sazon_kb.py
    python scripts/load_grupo_sazon_kb.py --path docs/OTHER_FILE.txt
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Ensure `backend/` is on sys.path when running as a plain script.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.services.vector_store import upsert_documents  # noqa: E402

logger = get_logger(__name__)

DEFAULT_PATH = BACKEND_DIR / "docs" / "GRUPO_SAZON_PUBLIC_INFO_ES.txt"

# Soft cap. Each section in the source doc is small, so we rarely split.
MAX_CHARS = 1500


def _split_sections(text: str) -> List[Tuple[str, str]]:
    """Split text into (section_title, chunk_body) tuples.

    Splits on blank-line boundaries (sections in this file follow that
    pattern). For oversized blocks, falls back to length-based chunks
    while preserving the section title at the top of each piece.
    """

    blocks = re.split(r"\n\s*\n", text.strip())
    sections: List[Tuple[str, str]] = []

    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue

        title = lines[0].strip()
        body = "\n".join(lines).strip()

        if len(body) <= MAX_CHARS:
            sections.append((title, body))
            continue

        buf: List[str] = [title]
        size = len(title)
        for line in lines[1:]:
            if size + len(line) + 1 > MAX_CHARS and len(buf) > 1:
                sections.append((title, "\n".join(buf).strip()))
                buf = [title]
                size = len(title)
            buf.append(line)
            size += len(line) + 1
        if len(buf) > 1:
            sections.append((title, "\n".join(buf).strip()))

    return sections


def load(path: Path = DEFAULT_PATH) -> int:
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")

    text = path.read_text(encoding="utf-8")
    sections = _split_sections(text)
    if not sections:
        logger.warning("No sections detected in %s", path)
        return 0

    documents = [body for _, body in sections]
    metadatas = [
        {
            "source": path.name,
            "section": title,
            "language": "es",
        }
        for title, _ in sections
    ]
    ids = [
        hashlib.sha1(f"{path.name}::{i}::{title}".encode("utf-8")).hexdigest()
        for i, (title, _) in enumerate(sections)
    ]

    n = upsert_documents(documents, ids=ids, metadatas=metadatas)
    logger.info(
        "Indexed %d chunks from %s into Chroma collection.", n, path.name
    )
    return n


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(
        description="Load a plain-text knowledge base into the Chroma store."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_PATH,
        help="Path to the source .txt file (default: Grupo Sazon public info).",
    )
    args = parser.parse_args()
    n = load(args.path)
    print(f"Indexed {n} chunks from {args.path.name}.")


if __name__ == "__main__":
    main()
