# EvoRAG Model Service

Python FastAPI microservice utilizing LangChain and LangGraph for adaptive retrieval-augmented generation (RAG).

## Features
- **LangGraph State Machine**: Manages the life cycle of query requests from retrieval through update classification.
- **Dynamic Web Search**: Automatically triggers web search when RAG confidence is low or information is stale.
- **Asynchronous Self-Updating**: Classifies incoming web results into `NEW`, `UPDATE`, `DUPLICATE`, `CONTRADICTION`, or `OBSOLETE` to maintain DB integrity.

## Setup & Running

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch FastAPI service
uvicorn app.main:app --reload --port 8000
```
