# FastAPI Backend API — AI Support Ticket Triage

Backend service implementation for the AI Customer Support Ticket Triage System.

For full system architecture, Compose orchestration docs, and Judge Q&A cheat sheet, refer to the [Root README.md](../README.md).

## Quick Start (Standalone Local Development)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run API Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Open API Documentation
- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc UI: `http://localhost:8000/redoc`

## Component Structure
```
api/
├── Dockerfile          # Production-grade Dockerfile with non-root security
├── requirements.txt    # Pinned Python dependencies with inline rationale
├── .dockerignore       # Build exclusion rules
└── app/
    ├── __init__.py      # Package initialization
    ├── main.py          # FastAPI application wiring & route handlers
    ├── config.py        # pydantic-settings configuration manager
    ├── schemas.py       # Pydantic request & response validation models
    ├── model_loader.py  # Singleton ML model deserialization & inference manager
    ├── logger.py        # 12-factor stdout logging setup
    └── exceptions.py    # Custom exception classes and global error handlers
```
