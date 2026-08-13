from embeddings import EmbeddingsEngine
from vector_store import DualVectorStore


def main():
    model_name = "snowflake/snowflake-arctic-embed-m"
    engine = EmbeddingsEngine(model_name)

    texts = [
        "This is a sample text for embedding test.",
        "The telecom bill payment and internet signal issue are being checked.",
        "Machine learning models generate vector representations for text."
    ]

    embeddings = engine.encode(texts)
    chunks = [
        {"text": text, "metadata": {"source": "demo", "id": idx}}
        for idx, text in enumerate(texts)
    ]

    store = DualVectorStore(
        dimension=engine.dimension,
        model_name=engine.model_name,
        pinecone_api_key=""
    )
    store.upsert_chunks(chunks, embeddings)

    first_meta = store.doc_chunks[0]["metadata"]
    print(f"Stored model: {first_meta['model_name']}")
    print(f"Stored dimension: {first_meta['embedding_dimension']}")
    print(f"Batch count: {len(embeddings)}")
    print(f"Vector shape: {embeddings[0].shape}")
    print(f"First vector sample: {embeddings[0][:10]}")


if __name__ == "__main__":
    main()
