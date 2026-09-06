import os
from dotenv import load_dotenv

load_dotenv()

# Qdrant Database Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_URL = os.getenv("QDRANT_URL", None)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "evorag_chunks")

# Cold Storage Archive Database Configuration (SQLite)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLD_STORAGE_DB_PATH = os.getenv("COLD_STORAGE_DB_PATH", os.path.join(BASE_DIR, "evorag_archive.db"))

# Retrieval & Staleness Assessment Configuration
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.70"))
MAX_AGE_DAYS = int(os.getenv("MAX_AGE_DAYS", "30"))

# Keywords indicating query requests recent/real-time information
_raw_keywords = os.getenv("RECENCY_KEYWORDS", "latest,current,now,2026,today,recent,newest,update,present")
RECENCY_KEYWORDS = [k.strip().lower() for k in _raw_keywords.split(",") if k.strip()]

# Embedding Model Configuration
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# Web Search Configuration
WEB_SEARCH_PROVIDER = os.getenv("WEB_SEARCH_PROVIDER", "tavily").lower()
WEB_SEARCH_API_KEY = (
    os.getenv("WEB_SEARCH_API_KEY")
    or os.getenv("TAVILY_API_KEY")
    or os.getenv("SERPAPI_API_KEY")
    or None
)
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))
WEB_SEARCH_SNIPPET_MAX_CHARS = int(os.getenv("WEB_SEARCH_SNIPPET_MAX_CHARS", "1000"))

# LLM Generation Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
LLM_API_KEY = (
    os.getenv("LLM_API_KEY")
    or os.getenv("GROQ_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or None
)
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "llama-3.1-8b-instant")

# Classification Configuration
CLASSIFICATION_MATCH_FLOOR = float(os.getenv("CLASSIFICATION_MATCH_FLOOR", "0.5"))

# Garbage Collection & Compaction Configuration
MAX_VERSION_HISTORY = int(os.getenv("MAX_VERSION_HISTORY", "2"))
DUPLICATE_SIMILARITY_THRESHOLD = float(os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.95"))
GC_INTERVAL_HOURS = int(os.getenv("GC_INTERVAL_HOURS", "24"))
