"""
build and load local rag corpus from official pdfs.

ingest: sources.json + pdfs -> corpus.jsonl
load: corpus.jsonl -> EvidenceChunk list for search
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pdfplumber

from .models import EvidenceChunk

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = BACKEND_ROOT / "rag_sources" / "sources.json"
DEFAULT_CORPUS = BACKEND_ROOT / "rag_index" / "corpus.jsonl"


def _clean(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text.replace("\u00a0", " ")).strip()
    text = re.sub(r"\b([A-Z])\s+([a-z]{2,})\b", r"\1\2", text)
    return re.sub(r"\b(\d)\s+(\d)%", r"\1\2%", text)


def _windows(text: str, size: int = 2200, overlap: int = 350) -> list[str]:
    """split page text into overlapping windows so rules stay together."""
    lines = [cleaned for line in text.splitlines() if (cleaned := _clean(line))]
    windows: list[str] = []
    current: list[str] = []
    length = 0
    for line in lines:
        if current and length + len(line) + 1 > size:
            windows.append("\n".join(current))
            tail: list[str] = []
            tail_size = 0
            for item in reversed(current):
                if tail_size + len(item) > overlap:
                    break
                tail.insert(0, item)
                tail_size += len(item) + 1
            current, length = tail, tail_size
        current.append(line)
        length += len(line) + 1
    if current:
        windows.append("\n".join(current))
    return windows


def build_corpus(
    manifest_path: Path = DEFAULT_MANIFEST,
    output_path: Path = DEFAULT_CORPUS,
) -> int:
    """read pdfs from manifest, write corpus.jsonl, return chunk count."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks: list[EvidenceChunk] = []
    for source in manifest["sources"]:
        pdf_path = manifest_path.parent / source["file"]
        if not pdf_path.is_file():
            raise FileNotFoundError(f"RAG source is missing: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                for index, window in enumerate(_windows(text)):
                    digest = hashlib.sha256(
                        f"{source['id']}:{page_number}:{index}:{window}".encode()
                    ).hexdigest()[:20]
                    chunks.append(
                        EvidenceChunk(
                            chunk_id=digest,
                            source_id=source["id"],
                            source_name=source["name"],
                            organisation=source["organisation"],
                            official_url=source["official_url"],
                            document_type=source["document_type"],
                            page=page_number,
                            text=window,
                        )
                    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as stream:
        for chunk in chunks:
            stream.write(json.dumps(chunk.__dict__, ensure_ascii=False) + "\n")
    return len(chunks)


def load_corpus(path: Path = DEFAULT_CORPUS) -> list[EvidenceChunk]:
    """load corpus.jsonl into EvidenceChunk objects."""
    if not path.is_file():
        raise FileNotFoundError(f"RAG corpus is missing: {path}")
    chunks: list[EvidenceChunk] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            chunks.append(EvidenceChunk(**json.loads(line)))
    return chunks
