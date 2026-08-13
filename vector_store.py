import os
import numpy as np
from dotenv import load_dotenv

load_dotenv()

DEFAULT_PINECONE_KEY = os.getenv("PINECONE_API_KEY", "pcsk_3RL8em_L1vjE3xj48SHE5Dr6rmgMiCJP8nmxcBqkN6caw68zXusXDvQRF5VdpsMsYrHv7k")
INDEX_NAME = "telecom-complaints"


class DualVectorStore:
    def __init__(self, dimension=384, index_name=INDEX_NAME, pinecone_api_key=DEFAULT_PINECONE_KEY, model_name="all-MiniLM-L6-v2"):
        """
        Dual Vector Store matching Untitled87.ipynb Pinecone configuration.
        Provides both Pinecone cloud index and FAISS local vector store fallback.
        """
        self.dimension = dimension
        self.index_name = index_name
        self.pinecone_api_key = pinecone_api_key
        self.model_name = model_name
        
        self.pinecone_index = None
        self.use_pinecone = False
        
        # Local Vector Store (FAISS / NumPy cosine memory)
        self.faiss_index = None
        self.doc_chunks = []  # Stores list of dicts: {"text": str, "metadata": dict}
        self.vectors = None

        self._init_pinecone()
        self._init_faiss()

    def _init_pinecone(self):
        if not self.pinecone_api_key:
            print("Pinecone API key not found. Using local FAISS vector store.")
            return

        try:
            from pinecone import Pinecone, ServerlessSpec, PodSpec
            print(f"Connecting to Pinecone index '{self.index_name}'...")
            pc = Pinecone(api_key=self.pinecone_api_key)
            
            existing_indexes = [idx.name for idx in pc.list_indexes()]
            if self.index_name not in existing_indexes:
                print(f"Creating Pinecone index '{self.index_name}'...")
                try:
                    pc.create_index(
                        name=self.index_name,
                        dimension=self.dimension,
                        metric='cosine',
                        spec=ServerlessSpec(cloud='aws', region='us-east-1')
                    )
                except Exception as e_create:
                    print(f"Pinecone create index notice: {e_create}. Trying PodSpec...")
                    pc.create_index(
                        name=self.index_name,
                        dimension=self.dimension,
                        metric='cosine',
                        spec=PodSpec(environment="aws-us-east-1")
                    )
            
            self.pinecone_index = pc.Index(self.index_name)
            self.use_pinecone = True
            print("Pinecone vector store connected successfully!")
        except Exception as e:
            print(f"Pinecone initialization info: {e}. Defaulting to FAISS vector store.")
            self.use_pinecone = False

    def _init_faiss(self):
        try:
            import faiss
            self.faiss_index = faiss.IndexFlatIP(self.dimension)  # Inner product for normalized vectors
        except Exception as e:
            print(f"FAISS load info: {e}. Using NumPy cosine matrix search.")
            self.faiss_index = None

    def upsert_chunks(self, chunks, embeddings):
        """
        Upserts vectors and metadata chunks into Pinecone and Local FAISS Store.
        matches Notebook workflow.
        """
        self.doc_chunks = []
        for chunk in chunks:
            doc = dict(chunk)
            metadata = dict(doc.get("metadata", {}))
            metadata["model_name"] = self.model_name
            metadata["embedding_dimension"] = int(self.dimension)
            doc["metadata"] = metadata
            self.doc_chunks.append(doc)

        self.vectors = np.array(embeddings, dtype=np.float32)

        # 1. Upsert into FAISS / Local store
        if self.faiss_index is not None:
            self.faiss_index.reset()
            self.faiss_index.add(self.vectors)

        # 2. Upsert into Pinecone if active
        if self.use_pinecone and self.pinecone_index is not None:
            try:
                pinecone_vectors = []
                for i, (chunk, emb) in enumerate(zip(self.doc_chunks, embeddings)):
                    vec_id = chunk["metadata"].get("complaint_id", f"doc_{i}")
                    # Sanitized metadata values for Pinecone (must be str, int, float, bool, or list of str)
                    meta = {}
                    for k, v in chunk["metadata"].items():
                        meta[k] = str(v)
                    meta["text"] = chunk["text"][:1000]  # truncate text for pinecone metadata limits
                    pinecone_vectors.append((vec_id, emb.tolist(), meta))

                # Batch upsert
                batch_size = 100
                for b in range(0, len(pinecone_vectors), batch_size):
                    self.pinecone_index.upsert(vectors=pinecone_vectors[b:b+batch_size])
                print(f"Successfully upserted {len(pinecone_vectors)} records to Pinecone index '{self.index_name}'.")
            except Exception as e:
                print(f"Pinecone upsert warning: {e}. Vectors indexed in local vector store.")

    def search(self, query_vector, top_k=5, metadata_filter=None):
        """
        Searches top_k vectors matching query_vector, with metadata filtering.
        Returns list of dicts: [{"chunk": dict, "score": float}]
        """
        query_vec = np.array(query_vector, dtype=np.float32)
        if len(query_vec.shape) == 1:
            query_vec = np.expand_dims(query_vec, axis=0)

        results = []

        # Try Pinecone search if available
        if self.use_pinecone and self.pinecone_index is not None:
            try:
                filter_dict = {}
                if metadata_filter:
                    for k, v in metadata_filter.items():
                        if v and v != "All":
                            filter_dict[k] = {"$eq": str(v)}

                res = self.pinecone_index.query(
                    vector=query_vec[0].tolist(),
                    top_k=top_k,
                    include_metadata=True,
                    filter=filter_dict if filter_dict else None
                )
                for match in res.get("matches", []):
                    results.append({
                        "chunk": {
                            "text": match.metadata.get("text", ""),
                            "metadata": match.metadata
                        },
                        "score": float(match.score)
                    })
                if len(results) > 0:
                    return results
            except Exception as e:
                print(f"Pinecone query warning: {e}. Fallback to local vector search.")

        # Local Vector Search (FAISS or NumPy cosine similarity)
        if self.vectors is None or len(self.vectors) == 0:
            return []

        if self.faiss_index is not None:
            scores, indices = self.faiss_index.search(query_vec, min(top_k * 3, len(self.doc_chunks)))
            raw_matches = zip(indices[0], scores[0])
        else:
            # Cosine similarity matrix multiplication
            sims = np.dot(self.vectors, query_vec[0])
            top_indices = np.argsort(sims)[::-1][:top_k * 3]
            raw_matches = zip(top_indices, sims[top_indices])

        for idx, score in raw_matches:
            if idx < 0 or idx >= len(self.doc_chunks):
                continue
            chunk = self.doc_chunks[idx]
            meta = chunk.get("metadata", {})

            # Apply metadata filter
            if metadata_filter:
                match_filter = True
                for fk, fval in metadata_filter.items():
                    if fval and fval != "All" and str(meta.get(fk, "")).lower() != str(fval).lower():
                        match_filter = False
                        break
                if not match_filter:
                    continue

            results.append({
                "chunk": chunk,
                "score": float(score)
            })
            if len(results) >= top_k:
                break

        return results
