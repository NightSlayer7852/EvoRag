import hashlib
import numpy as np
from typing import List
from app.config import EMBEDDING_MODEL_NAME

_embeddings_instance = None


def get_embedding_model():
    """
    Lazy initialization of embedding model using LangChain / SentenceTransformers.
    Falls back to a deterministic hash vectorizer if model loading is unavailable.
    """
    global _embeddings_instance
    if _embeddings_instance is not None:
        return _embeddings_instance

    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        _embeddings_instance = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        return _embeddings_instance
    except Exception as e:
        print(f"[Embeddings] Notice: HuggingFaceEmbeddings unavailable ({e}). Using deterministic fallback embedder.")
        _embeddings_instance = "fallback"
        return _embeddings_instance


def embed_text(text: str) -> List[float]:
    """
    Generates vector embedding for input text.
    
    Args:
        text (str): Input string to embed.

    Returns:
        List[float]: High-dimensional embedding vector.
    """
    model = get_embedding_model()
    if model != "fallback":
        try:
            return model.embed_query(text)
        except Exception:
            pass

    # Deterministic fallback vectorizer (384 dimensions) for offline/standalone execution
    dim = 384
    hash_bytes = hashlib.sha256(text.encode('utf-8')).digest()
    np.random.seed(int.from_bytes(hash_bytes[:4], 'big'))
    vector = np.random.uniform(-1.0, 1.0, dim)
    norm = np.linalg.norm(vector)
    return (vector / norm).tolist()
