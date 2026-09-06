import os
from dotenv import load_dotenv

load_dotenv()

# Qdrant Database Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_URL = os.getenv("QDRANT_URL", None)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "evorag_chunks")

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
