# AI Health Agent Dashboard

## Overview

**AI Health Agent Dashboard** is a portfolio prototype for **prior authorization review in healthcare imaging**. It demonstrates how a narrow, high-friction workflow, gathering case facts, checking payer policy criteria, and preparing review-ready justification, can be supported with a modular AI system rather than a generic chatbot.

The project focuses on a safe, local-first demo setup:
- **Synthetic patient cases** modeled after EHR-style imaging requests
- **Public insurer policy PDFs** used as the evidence source for retrieval
- **No live PHI, EHR, or payer portal integrations**

At a high level, the system:
- loads and normalizes synthetic patient cases into a structured domain model
- ingests payer policy PDFs, extracts and chunks text, and indexes them for retrieval
- retrieves relevant policy evidence for a selected case
- orchestrates structured review artifacts for prior auth reasoning
- exposes the workflow through a **FastAPI backend**
- provides a **React + TypeScript dashboard** where a reviewer can submit a case, select a case, and chat over grounded workflow results

## What Problem It Solves

Prior authorization for imaging is a costly administrative bottleneck. Staff often need to manually answer questions like:
- What imaging study was ordered?
- How long has the patient had symptoms?
- Has conservative therapy already been tried?
- Was prior imaging completed first?
- What payer policy language supports approval or follow-up?

This prototype shows how AI can reduce that friction by turning case inputs and policy documents into a **reviewable, evidence-backed workflow**.

## Key Features

- **Structured case intake**
  - Loads synthetic JSON/text cases and normalizes them into stable typed models
- **Policy ingestion and retrieval**
  - Processes public policy PDFs into a searchable evidence corpus
- **Grounded prior auth reasoning**
  - Connects case facts to retrieved payer policy evidence
- **Deterministic validation**
  - Keeps key checks outside free-form LLM behavior
- **Case-level chatbot**
  - Lets reviewers ask questions about a selected case using workflow artifacts and citations
- **Modular architecture**
  - Separates domain, ingestion, retrieval, orchestration, API, chat, and UI concerns

## Data Used

- **Synthetic case data**
  - Mock patient cases for approval-like, denial-like, and ambiguous scenarios
  - Seeded examples live under `tmp/`
- **Public payer policy PDFs**
  - Local source documents stored in `data/` for evidence retrieval
- **No production healthcare data**
  - No PHI, no live EHR records, and no insurer integrations

## Tech Stack

**Backend**
- Python 3.12+
- Pydantic
- FastAPI
- Uvicorn

**AI / Retrieval**
- CrewAI-style multi-agent orchestration concepts
- SiliconFlow-based chat model integration
- Sentence Transformers for local embeddings
- ChromaDB-compatible vector-store abstraction

**Frontend**
- React
- TypeScript
- Vite

## Architecture

The repository is organized into distinct modules so each concern stays isolated:

- `src/domain/`
  - canonical schemas and shared enums
- `src/data_ingestion/`
  - policy PDF discovery, parsing, chunking, embedding, indexing
- `src/case_intake/`
  - synthetic case loading, parsing, normalization, building
- `src/retrieval/`
  - query building, vector search, policy evidence mapping
- `src/agents/`
  - extractor, policy matcher, form filler runtime layers
- `src/rules_engine/`
  - deterministic checks outside agent reasoning
- `src/orchestration/`
  - workflow execution, handoffs, policies, CrewAI adapter
- `src/api/`
  - FastAPI app, routes, dependencies, store
- `src/chat/`
  - flexible chat models and SiliconFlow adapter
- `ui/`
  - React review dashboard

## How To Access It Locally

### 1. Install backend dependencies

From the repo root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Optional extras:

```bash
pip install -e .[dev]
pip install -e .[crewai]
```

### 2. Configure environment variables

Create a root `.env` file:

```env
SILICONFLOW_API_KEY=your_key_here
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-V3.2
SILICONFLOW_BASE_URL=https://api.siliconflow.com/v1
```

Notes:
- `SILICONFLOW_API_KEY` is required only for live chatbot responses.
- The case workflow itself can still run in **mock crew** mode for local demos.
- Install `.[crewai]` only if you want live CrewAI-backed workflow agents instead of mock crews.

### 3. Start the backend API

From the repo root:

```bash
PYTHONPATH=src uvicorn api.app:app --reload
```

The API will be available at:

- `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`

### 4. Start the frontend

In a second terminal:

```bash
cd ui
npm install
npm run dev
```

The UI will be available at:

- `http://127.0.0.1:5173`

### 5. Use the demo

In the dashboard:
- submit a seeded synthetic case such as `tmp/case-001.json`
- keep `data` as the policy directory
- enable **mock crews** for a local non-LLM workflow demo if needed
- select the submitted case
- ask grounded questions in the chatbot

Seeded test cases live in:

- `tmp/case-001.json`
- `tmp/case-002.json` through `tmp/case-015.json`

## Local Deployment Notes

For a recruiter demo, the simplest deployment is:

1. Run the FastAPI backend locally with `uvicorn`
2. Run the Vite frontend locally with `npm run dev`
3. Open the UI in the browser and use the seeded case dropdown

For a more production-like local preview:

```bash
cd ui
npm run build
npm run preview
```

This serves the built frontend locally, while the backend still runs separately on port `8000`.

## Example Demo Flow

1. Start the backend and frontend
2. Open `http://127.0.0.1:5173`
3. Submit `tmp/case-002.json`
4. Select the case from the case list
5. Ask prompts such as:
   - `Why does this case appear to meet policy criteria?`
   - `What evidence supports the current recommendation?`
   - `What is missing or still ambiguous in this case?`

## Current Scope

This is a **prototype demo**, not a production clinical system.

Current constraints:
- synthetic patient-like data only
- public payer policy PDFs only
- no real payer portal automation
- no real EHR integration
- human review remains the final decision layer

## Why This Project Matters

This project is designed to show more than basic prompt engineering. It demonstrates:
- domain-focused product thinking
- modular backend architecture
- document ingestion and retrieval
- evidence-grounded AI behavior
- deterministic validation in a regulated-style workflow
- full-stack integration from workflow engine to user interface

In short, this is a practical prototype for **AI-assisted prior authorization review**, built to be transparent, testable, and easy to demo.
