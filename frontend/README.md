# EvoRAG Frontend Application

The React + Vite frontend provides an interactive user interface for querying EvoRAG, viewing source attributions (RAG Vector Store, Live Web Search, Confidence score), and triggering database garbage collection / compaction background jobs.

## Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Verify `VITE_BACKEND_URL` points to the running Node.js Express backend (default: `http://localhost:5000/api`).

## How to Run End-to-End

To run the complete EvoRAG end-to-end stack:

1. **Start Model FastAPI Microservice**:
   ```bash
   cd model
   uvicorn app.main:app --reload --port 8000
   ```

2. **Start Express Backend Orchestration Service**:
   ```bash
   cd backend
   npm run dev
   ```

3. **Start React Frontend Dev Server**:
   ```bash
   cd frontend
   npm run dev
   ```

4. Open the displayed Vite URL (e.g. `http://localhost:5173`) in your browser to interact with EvoRAG.
