from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from app.graphs.evorag_graph import run_evorag_pipeline
from app.schemas.answer_schema import AnswerResult
from app.services.gc_service import run_garbage_collection
from app.services.archive_service import ArchiveService
from app.jobs.gc_scheduler import start_gc_scheduler

archive_service = ArchiveService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background GC scheduler
    start_gc_scheduler()
    yield
    # Shutdown logic if any
    pass


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


@app.get("/")
def read_root():
    return {"message": "EvoRAG Model Service is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/query", response_model=AnswerResult)
def process_query(payload: dict, background_tasks: BackgroundTasks):
    """
    POST /query endpoint called by Node.js backend or web frontend.
    Executes LangGraph state machine and dispatches async memory self-updating tasks.
    """
    query = payload.get("query", "").strip()
    if not query:
        return AnswerResult(
            answer="Invalid request: Empty query provided.",
            used_rag=False,
            used_web=False,
            confidence_score=0.0
        )

    result = run_evorag_pipeline(query=query, background_tasks=background_tasks)
    return result


@app.post("/gc/run")
def trigger_garbage_collection():
    """
    POST /gc/run on-demand endpoint for triggering vector DB garbage collection & compaction.
    """
    summary = run_garbage_collection()
    return {"status": "success", "summary": summary}


@app.get("/archive/chunks")
def list_archived_chunks(limit: int = 50):
    """
    GET /archive/chunks endpoint returning recent cold-tier archived records for UI status panel.
    """
    records = archive_service.list_archived(limit=limit)
    return {"count": len(records), "archived_chunks": records}
