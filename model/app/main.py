import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    PORT, LLM_PROVIDER, LLM_MODEL_NAME, QDRANT_CLUSTER_ENDPOINT, QDRANT_HOST, QDRANT_PORT,
    CONFIDENCE_THRESHOLD, GC_INTERVAL_HOURS, QDRANT_COLLECTION_NAME
)
from app.graphs.evorag_graph import run_evorag_pipeline
from app.schemas.answer_schema import AnswerResult
from app.services.gc_service import run_garbage_collection
from app.services.archive_service import ArchiveService
from app.jobs.gc_scheduler import start_gc_scheduler

logger = logging.getLogger("evorag.main")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

archive_service = ArchiveService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: log configuration and start background GC scheduler
    logger.info("=" * 60)
    logger.info("EvoRAG Model Service — STARTUP")
    logger.info("=" * 60)
    logger.info(f"  LLM Provider    : {LLM_PROVIDER}")
    logger.info(f"  LLM Model       : {LLM_MODEL_NAME}")
    qdrant_target = QDRANT_CLUSTER_ENDPOINT or f"{QDRANT_HOST}:{QDRANT_PORT}"
    logger.info(f"  Qdrant Target   : {qdrant_target}")
    logger.info(f"  Collection      : {QDRANT_COLLECTION_NAME}")
    logger.info(f"  Conf Threshold  : {CONFIDENCE_THRESHOLD}")
    logger.info(f"  GC Interval     : every {GC_INTERVAL_HOURS}h")
    logger.info("=" * 60)
    start_gc_scheduler()
    logger.info("Background GC scheduler started.")
    yield
    logger.info("EvoRAG Model Service — SHUTDOWN")


app = FastAPI(
    title="EvoRAG Model Service",
    description="Python FastAPI service exposing LangGraph adaptive RAG and self-updating memory pipeline.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every HTTP request with method, path, and response time."""
    start = time.perf_counter()
    logger.info(f"→ {request.method} {request.url.path}")
    response: Response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    logger.info(f"← {request.method} {request.url.path} [{response.status_code}] ({elapsed:.1f}ms)")
    return response


@app.get("/")
def read_root():
    return {"message": "EvoRAG Model Service is running"}


@app.get("/health")
def health_check():
    logger.debug("[Health] Health check requested")
    return {"status": "ok"}


@app.post("/query", response_model=AnswerResult)
def process_query(payload: dict, background_tasks: BackgroundTasks):
    """
    POST /query endpoint called by Node.js backend or web frontend.
    Executes LangGraph state machine and dispatches async memory self-updating tasks.
    """
    query = payload.get("query", "").strip()
    logger.info(f"[Query] Processing: \"{query[:100]}{'...' if len(query) > 100 else ''}\"")

    if not query:
        logger.warning("[Query] Rejected — empty query received")
        return AnswerResult(
            answer="Invalid request: Empty query provided.",
            used_rag=False,
            used_web=False,
            confidence_score=0.0
        )

    t = time.perf_counter()
    result = run_evorag_pipeline(query=query, background_tasks=background_tasks)
    elapsed = (time.perf_counter() - t) * 1000
    logger.info(
        f"[Query] Completed in {elapsed:.0f}ms — "
        f"used_rag={result.used_rag} used_web={result.used_web} "
        f"confidence={result.confidence_score:.2f} "
        f"rag_chunks={len(result.rag_chunk_ids)} web_results={len(result.web_result_ids)}"
    )
    return result


@app.post("/gc/run")
def trigger_garbage_collection():
    """
    POST /gc/run on-demand endpoint for triggering vector DB garbage collection & compaction.
    """
    logger.info("[GC] Manual GC run triggered via API")
    t = time.perf_counter()
    summary = run_garbage_collection()
    elapsed = (time.perf_counter() - t) * 1000
    logger.info(f"[GC] Completed in {elapsed:.0f}ms — summary: {summary}")
    return {"status": "success", "summary": summary}


@app.get("/archive/chunks")
def list_archived_chunks(limit: int = 50):
    """
    GET /archive/chunks endpoint returning recent cold-tier archived records for UI status panel.
    """
    logger.debug(f"[Archive] Fetching archived chunks (limit={limit})")
    records = archive_service.list_archived(limit=limit)
    logger.info(f"[Archive] Returning {len(records)} archived chunk records")
    return {"count": len(records), "archived_chunks": records}
