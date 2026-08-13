from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

try:
    from langchain_core.documents import Document
except Exception:  # pragma: no cover
    Document = None

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:  # pragma: no cover
    RecursiveCharacterTextSplitter = None


class LangChainDocumentBuilder:
    """Thin adapter that converts internal chunks to LangChain document objects when available."""

    def __init__(self, chunker=None, chunk_size: int = 256, chunk_overlap: int = 32):
        self.chunker = chunker
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def build_documents(self, records: Iterable[Dict[str, Any]], source_type: str = "document") -> List[Any]:
        if self.chunker is None:
            from rag_engine.chunking import DocumentChunker
            self.chunker = DocumentChunker(max_tokens=self.chunk_size, overlap_tokens=self.chunk_overlap)

        docs: List[Any] = []
        for record in records:
            chunks = self.chunker.chunk_record(record, source_type=source_type)
            for chunk in chunks:
                metadata = dict(chunk.metadata)
                page_content = chunk.text
                if Document is not None:
                    docs.append(Document(page_content=page_content, metadata=metadata))
                else:
                    docs.append({"page_content": page_content, "metadata": metadata})
        return docs

    def build_langchain_splitter(self, **kwargs):
        if RecursiveCharacterTextSplitter is None:
            return None
        return RecursiveCharacterTextSplitter(
            chunk_size=kwargs.get("chunk_size", self.chunk_size),
            chunk_overlap=kwargs.get("chunk_overlap", self.chunk_overlap),
            separators=["\n\n", "\n", ". ", " ", ""],
        )


def to_langchain_documents(records: Iterable[Dict[str, Any]], source_type: str = "document", chunk_size: int = 256, chunk_overlap: int = 32):
    builder = LangChainDocumentBuilder(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return builder.build_documents(records, source_type=source_type)
