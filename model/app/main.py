from fastapi import FastAPI

app = FastAPI(title="EvoRAG Model Service")

@app.get("/")
def read_root():
    return {"message": "EvoRAG Model Service is running"}

@app.post("/query")
def handle_query(payload: dict):
    # Endpoint called by Node.js backend
    query = payload.get("query", "")
    return {
        "query": query,
        "answer": "Stub response from Python model service",
        "source": "RAG"
    }
