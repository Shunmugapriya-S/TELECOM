from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class Chunk:
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    source_type: str = "document"
    index: int = 0


class DocumentChunker:
    """Token-aware chunking and optimization layer for RAG document ingestion."""

    def __init__(self, max_tokens: int = 256, overlap_tokens: int = 32, min_chunk_tokens: int = 80):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_tokens = min_chunk_tokens

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(text))
        except Exception:
            return max(1, int(len(text.split()) * 1.3))

    def split_text(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []

        try:
            import tiktoken
            encoder = tiktoken.get_encoding("cl100k_base")
            tokens = encoder.encode(text)
        except Exception:
            tokens = text.split()

        if len(tokens) <= self.max_tokens:
            return [text]

        chunks: List[str] = []
        step = max(1, self.max_tokens - self.overlap_tokens)
        start = 0

        while start < len(tokens):
            end = min(start + self.max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            try:
                chunk_text = tiktoken.get_encoding("cl100k_base").decode(chunk_tokens)
            except Exception:
                chunk_text = " ".join(tokens[start:end])

            chunks.append(chunk_text.strip())
            if end >= len(tokens):
                break
            start += step

        return [chunk for chunk in chunks if chunk and chunk.strip()]

    def optimize_chunks(self, chunks: Iterable[Chunk]) -> List[Chunk]:
        optimized: List[Chunk] = []
        for chunk in chunks:
            if chunk.token_count <= self.max_tokens:
                optimized.append(chunk)
                continue

            sub_chunks = self.split_text(chunk.text)
            for index, text in enumerate(sub_chunks):
                optimized.append(
                    Chunk(
                        text=text,
                        metadata=dict(chunk.metadata),
                        token_count=self.count_tokens(text),
                        source_type=chunk.source_type,
                        index=index,
                    )
                )

        merged: List[Chunk] = []
        buffer: Optional[Chunk] = None

        for chunk in optimized:
            if buffer is None:
                buffer = chunk
                continue

            combined_text = f"{buffer.text}\n\n{chunk.text}".strip()
            combined_tokens = self.count_tokens(combined_text)

            if combined_tokens <= self.max_tokens or buffer.token_count < self.min_chunk_tokens:
                buffer = Chunk(
                    text=combined_text,
                    metadata={**buffer.metadata, **chunk.metadata},
                    token_count=combined_tokens,
                    source_type=buffer.source_type,
                    index=buffer.index,
                )
            else:
                merged.append(buffer)
                buffer = chunk

        if buffer is not None:
            merged.append(buffer)

        return merged

    def chunk_record(self, record: Dict[str, Any], source_type: str = "document") -> List[Chunk]:
        raw_text = str(record.get("raw_text") or record.get("text") or record.get("content") or "").strip()
        if not raw_text:
            return []

        metadata = dict(record.get("metadata", {}))
        for key, value in record.items():
            if key in {"raw_text", "text", "content", "metadata"}:
                continue
            metadata.setdefault(key, value)

        chunks = []
        for index, text in enumerate(self.split_text(raw_text)):
            chunk = Chunk(
                text=text,
                metadata={**metadata, "source_type": source_type, "chunk_index": index},
                token_count=self.count_tokens(text),
                source_type=source_type,
                index=index,
            )
            chunks.append(chunk)

        return self.optimize_chunks(chunks)

    def chunk_records(self, records: Iterable[Dict[str, Any]], source_type: str = "document") -> List[Chunk]:
        chunks: List[Chunk] = []
        for record in records:
            chunks.extend(self.chunk_record(record, source_type=source_type))
        return chunks

    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None, source_type: str = "document") -> List[Chunk]:
        metadata = metadata or {}
        chunks = []
        for index, segment in enumerate(self.split_text(text)):
            chunks.append(
                Chunk(
                    text=segment,
                    metadata={**metadata, "source_type": source_type, "chunk_index": index},
                    token_count=self.count_tokens(segment),
                    source_type=source_type,
                    index=index,
                )
            )
        return self.optimize_chunks(chunks)


def chunk_documents(records: Iterable[Dict[str, Any]], max_tokens: int = 256, overlap_tokens: int = 32, min_chunk_tokens: int = 80) -> List[Chunk]:
    chunker = DocumentChunker(max_tokens=max_tokens, overlap_tokens=overlap_tokens, min_chunk_tokens=min_chunk_tokens)
    return chunker.chunk_records(records)
