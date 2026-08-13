from rag_engine.embeddings import EmbeddingsEngine
from rag_engine.vector_store import DualVectorStore
from rag_engine.chunking import DocumentChunker
from rag_engine.langchain_module import LangChainDocumentBuilder
from rag_engine.context_engineering import ContextEngineer
from data_pipeline import load_data, clean_data, load_kb_docs


class TelecomRAGRetriever:
    def __init__(self):
        """
        Retriever wrapping Embeddings Engine, chunk optimizer, LangChain adapter,
        and Dual Vector Store.
        """
        self.embeddings_engine = EmbeddingsEngine()
        self.chunker = DocumentChunker(max_tokens=256, overlap_tokens=32, min_chunk_tokens=80)
        self.langchain_builder = LangChainDocumentBuilder(chunker=self.chunker, chunk_size=256, chunk_overlap=32)
        self.context_engineer = ContextEngineer(max_context_chars=4000, max_chunks=5, min_score=0.0)
        self.vector_store = DualVectorStore(
            dimension=self.embeddings_engine.dimension,
            model_name=self.embeddings_engine.model_name
        )
        self.is_indexed = False

    def index_documents(self):
        """
        Converts raw complaint and KB documents into optimized chunks,
        builds LangChain documents, and indexes embeddings.
        """
        print("Loading Telecom Complaints & SOP Knowledge Base...")
        records = load_data()
        cleaned_records = clean_data(records)
        kb_docs = load_kb_docs()

        complaint_chunk_objs = self.chunker.chunk_records(cleaned_records, source_type="complaint")
        kb_chunk_objs = self.chunker.chunk_records(kb_docs, source_type="kb")

        all_chunks = []
        for chunk in complaint_chunk_objs + kb_chunk_objs:
            all_chunks.append({
                "text": chunk.text,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata,
            })

        langchain_docs = self.langchain_builder.build_documents(
            [{"text": chunk["text"], "metadata": chunk["metadata"]} for chunk in all_chunks],
            source_type="document"
        )

        texts = [chunk["text"] for chunk in all_chunks]
        print(f"Generating embeddings for {len(texts)} optimized chunks using SentenceTransformer...")
        embeddings = self.embeddings_engine.encode(texts, normalize_embeddings=True)

        self.vector_store.model_name = self.embeddings_engine.model_name
        self.vector_store.dimension = self.embeddings_engine.dimension

        print("Upserting vectors into Dual Vector Store (Pinecone + FAISS)...")
        self.vector_store.upsert_chunks(all_chunks, embeddings)
        self.is_indexed = True
        print(f"Vector Store indexing complete! Total documents indexed: {len(all_chunks)}")
        print(f"LangChain documents created: {len(langchain_docs)}")

    def retrieve(self, query, top_k=4, category=None, language=None, sentiment=None, priority=None):
        """
        Retrieves top_k relevant context chunks for a customer query with metadata filters.
        """
        if not self.is_indexed:
            self.index_documents()

        query_vector = self.embeddings_engine.encode(query, normalize_embeddings=True)

        metadata_filter = {}
        if category and category != "All":
            metadata_filter["category"] = category
        if language and language != "All":
            metadata_filter["language"] = language
        if sentiment and sentiment != "All":
            metadata_filter["sentiment"] = sentiment
        if priority and priority != "All":
            metadata_filter["priority"] = priority

        results = self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
            metadata_filter=metadata_filter if metadata_filter else None
        )
        return results

    def format_retrieved_context(self, search_results):
        """
        Formats retrieved search results into a clean string context block for the LLM prompt.
        """
        context_blocks = []
        for i, res in enumerate(search_results, 1):
            chunk = res["chunk"]
            score = res["score"]
            meta = chunk.get("metadata", {})
            doc_type = meta.get("doc_type", "customer_complaint")

            if doc_type == "telecom_sop":
                block = (
                    f"[Context Block {i} - SOP Resolution Guide (Score: {score:.3f})]\n"
                    f"Title: {meta.get('title', '')}\n"
                    f"Category: {meta.get('category', '')}\n"
                    f"Resolution Guide: {meta.get('content', '')}\n"
                    f"Action: {meta.get('action_required', '')}\n"
                )
            else:
                block = (
                    f"[Context Block {i} - Historical Complaint #{meta.get('complaint_id', '')} (Score: {score:.3f})]\n"
                    f"Customer Complaint: {meta.get('raw_text', '')}\n"
                    f"Category: {meta.get('category', '')} -> {meta.get('sub_category', '')}\n"
                    f"Intent: {meta.get('intent', '')} | Severity: {meta.get('severity', '')} | Priority: {meta.get('priority', '')}\n"
                    f"Sentiment: {meta.get('sentiment', '')} ({meta.get('emotion', '')})\n"
                )

            context_blocks.append(block)

        return "\n".join(context_blocks)

