# EvoRAG

An evolving Retrieval-Augmented Generation (RAG) system with query-triggered web search and asynchronous database self-updating.

## System Architecture

The repository is organized into three primary layers:

- **`backend/` (Node.js + Express API & Orchestration)**: API router and service layer connecting frontend requests with the model service, active vector store, cold archive storage, and garbage collection jobs.
- **`model/` (Python LangChain + LangGraph Service)**: Fast-API service implementing stateful LangGraph execution paths for hybrid retrieval, confidence/staleness evaluation, web search fallback, answer synthesis, and async memory updating.
- **`frontend/` (React)**: User interface for interactive querying, visualization of answer metadata/sources, and storage metrics monitoring.

## Directory Overview

```
EvoRAG/
├── backend/    # Node.js + Express API server
├── frontend/   # React web application
└── model/      # Python LangChain / LangGraph AI service
```
