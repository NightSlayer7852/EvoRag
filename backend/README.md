# EvoRAG Backend Microservice

The Node.js + Express backend acts as an API orchestration layer sitting between the React frontend UI and the Python `model/` FastAPI microservice.

## Environment Variables

Copy `.env.example` to `.env` or set the following variables:
- `PORT`: Port on which the Express server listens (default: `5000`)
- `MODEL_SERVICE_URL`: URL of the Python FastAPI service (default: `http://localhost:8000`)
- `FRONTEND_ORIGIN`: Allowed origin for CORS (default: `http://localhost:3000`)

## How to Run & Test

1. **Start Model FastAPI Service**:
   ```bash
   cd model
   uvicorn app.main:app --reload --port 8000
   ```

2. **Start Backend Server**:
   ```bash
   cd backend
   npm run dev
   # or node src/server.js
   ```

3. **Verify API Endpoints via Curl**:

   - **Health Check**:
     ```bash
     curl http://localhost:5000/api/health
     ```

   - **Query Execution**:
     ```bash
     curl -X POST http://localhost:5000/api/query \
       -H "Content-Type: application/json" \
       -d '{"query": "What is EvoRAG?"}'
     ```

   - **Trigger Garbage Collection Job**:
     ```bash
     curl -X POST http://localhost:5000/api/gc/run
     ```
