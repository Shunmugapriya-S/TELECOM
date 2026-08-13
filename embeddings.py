import numpy as np

SUPPORTED_MODELS = {
    "all-MiniLM-L6-v2": {"provider": "SentenceTransformers", "dim": 384, "desc": "Notebook Default - Fast 384d model"},
    "BAAI/bge-small-en-v1.5": {"provider": "HuggingFace", "dim": 384, "desc": "BAAI High-performance 384d model"},
    "intfloat/multilingual-e5-small": {"provider": "HuggingFace", "dim": 384, "desc": "Multilingual E5 (English, Tamil, Hindi)"},
    "snowflake/snowflake-arctic-embed-m": {"provider": "HuggingFace", "dim": 768, "desc": "Snowflake Arctic 768d embedding model"},
    "nvidia/NV-Embed-v2": {"provider": "NVIDIA / HuggingFace", "dim": 1024, "desc": "NVIDIA High-accuracy LLM embedding model"}
}


class EmbeddingsEngine:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        """
        Multi-model embedding engine supporting SentenceTransformers, HuggingFace, and NVIDIA models.
        """
        self.model_name = model_name
        self._st_model = None
        self._fallback_tfidf = None
        self.dimension = SUPPORTED_MODELS.get(model_name, {}).get("dim", 384)

    def change_model(self, model_name):
        self.model_name = model_name
        self._st_model = None
        self.dimension = SUPPORTED_MODELS.get(model_name, {}).get("dim", 384)
        print(f"Changed embedding model to: {model_name} (Dimension: {self.dimension})")

    def _init_st_model(self):
        if self._st_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"Loading embedding model '{self.model_name}'...")
                self._st_model = SentenceTransformer(self.model_name)

                if hasattr(self._st_model, "get_embedding_dimension"):
                    self.dimension = self._st_model.get_embedding_dimension()
                elif hasattr(self._st_model, "get_sentence_embedding_dimension"):
                    self.dimension = self._st_model.get_sentence_embedding_dimension()
                else:
                    self.dimension = SUPPORTED_MODELS.get(self.model_name, {}).get("dim", self.dimension)
            except Exception as e:
                print(f"Model '{self.model_name}' load info: {e}. Using TF-IDF/Dense vector representation.")
                from sklearn.feature_extraction.text import TfidfVectorizer
                self._fallback_tfidf = TfidfVectorizer(max_features=self.dimension)

    def encode(self, texts, normalize_embeddings=True):
        """
        Encodes texts into normalized numpy embeddings.
        """
        self._init_st_model()
        is_single = isinstance(texts, str)
        text_list = [texts] if is_single else texts

        if self._st_model is not None:
            emb = self._st_model.encode(text_list, normalize_embeddings=normalize_embeddings)
            return emb[0] if is_single else np.array(emb)
        else:
            if not hasattr(self._fallback_tfidf, "vocabulary_"):
                self._fallback_tfidf.fit(text_list + ["telecom internet bill recharge network 5G signal call dropped"])
            matrix = self._fallback_tfidf.transform(text_list).toarray()
            if matrix.shape[1] < self.dimension:
                matrix = np.pad(matrix, ((0, 0), (0, self.dimension - matrix.shape[1])))
            else:
                matrix = matrix[:, :self.dimension]
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            norm_emb = matrix / norms
            return norm_emb[0] if is_single else norm_emb

