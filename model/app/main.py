from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from app.graphs.evorag_graph import run_evorag_pipeline
from app.schemas.answer_schema import AnswerResult

app = FastAPI(
    title="EvoRAG Model Service",
    description="Python FastAPI service exposing LangGraph adaptive RAG and self-updating memory pipeline.",
    version="1.0.0"
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
