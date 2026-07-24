# Report 9: Methods and Decisions

**Project Title:** AI Customer Support Ticket Triage System  
**Author / Role:** Member 2 (FastAPI Backend, Docker, and Systems Integration)  
**Repository:** [https://github.com/antonyrahul07/ticket-triage-system](https://github.com/antonyrahul07/ticket-triage-system)

---

## 1. Executive Summary

This report documents the architectural, algorithmic, and infrastructure methods selected during the engineering of the **AI Customer Support Ticket Triage System**. The primary objective was to build a production-grade, low-latency microservice architecture capable of ingesting raw customer support tickets, validating inputs, executing real-time machine learning inference, and outputting structured department queue assignments, ticket types, priority levels, and confidence scores.

---

## 2. Machine Learning Algorithm Selection & Rationale

### 2.1 Algorithm Choice: TF-IDF + Logistic Regression
For text vectorization and classification, the machine learning pipeline utilizes **TF-IDF (Term Frequency-Inverse Document Frequency)** paired with a **Logistic Regression Classifier**.

- **TF-IDF Vectorization**: Transforms raw textual ticket data (subject + description) into high-dimensional numerical feature vectors. Term Frequency measures local word importance, while Inverse Document Frequency penalizes universally common stop-words (`"the"`, `"issue"`, `"system"`), amplifying domain-specific signals (`"overcharged"`, `"password"`, `"500 error"`).
- **Logistic Regression Classifier**: Computes linear decision boundaries across categories (`Technical`, `Billing`, `Account`, `General`).

### 2.2 Decision Rationale: Classical ML vs. Large Language Models (LLMs)
During architectural design, classical machine learning was chosen over LLMs (e.g., GPT-4/Llama) for three critical business reasons:
1. **Sub-5ms Inference Latency**: Classical TF-IDF vectorization and matrix multiplication execute in `< 5ms` per request, whereas LLM API calls require `1,000ms–3,000ms`, violating SLA requirements for high-volume support triage.
2. **Zero Inference Cost**: Local model evaluation runs at `$0` incremental cost per request, avoiding token-based API billing escalations.
3. **Calibrated Confidence Probabilities**: Logistic Regression natively outputs calibrated probability distributions via `predict_proba()`. This enables reliable confidence thresholding for human-in-the-loop safeguards.

---

## 3. Backend System Architecture & Design Decisions

### 3.1 Framework Selection: FastAPI & Pydantic v2
- **FastAPI**: Selected for its asynchronous ASGI request handling, performance parity with NodeJS/Go, and native OpenAPI/Swagger documentation generation (`/docs`).
- **Pydantic v2**: Enforces strict payload validation at the API edge (`TicketRequest`). Non-compliant payloads are rejected with HTTP 422 before reaching the model, preventing invalid data pollution.
- **pydantic-settings**: Enforces 12-Factor App methodology by parsing environment variables with type casting and fallbacks.

### 3.2 Performance Optimization: Singleton `ModelLoader` with `@lru_cache`
- **Problem**: Deserializing `.joblib` model artifacts on every incoming HTTP request causes severe disk I/O bottlenecks (100ms+ overhead per request).
- **Decision**: Implemented a singleton `ModelLoader` wrapped in `@lru_cache`. The model artifact is loaded into memory **once** during application startup (lifespan handler), enabling warm in-memory inference across all subsequent API requests.

---

## 4. Container Orchestration & Security Decisions

### 4.1 3-Tier Microservice Orchestration (Docker Compose)
The application environment is decoupled into three distinct services:
1. `triage_trainer`: One-shot training batch job.
2. `triage_api`: Long-running REST API.
3. `triage_evaluator`: One-shot metric evaluation job.

### 4.2 Decoupled Data Persistence & Volume Management
- **Shared Volume (`models_data`)**: The ML model artifact is shared between containers via a named Docker volume mounted **Read-Only (`:ro`)** into the API container.
- **Architectural Rationale**: Decouples MLOps (model retraining) from DevOps (API infrastructure). The API image is compiled once and remains immutable; model weights update dynamically via the mounted volume.

### 4.3 Boot Race-Condition Prevention
- Implemented Docker Compose v2 `depends_on: condition: service_completed_successfully`. The API container waits for `triage_trainer` to exit with status code 0 before booting, completely eliminating runtime `ModelNotFoundError` startup crashes.

### 4.4 Container Security & Hardening
- **Base Image**: `python:3.11-slim` minimizes OS package attack surface.
- **Non-Root Execution**: Runs under a dedicated unprivileged user (`USER appuser`) following the Principle of Least Privilege.
- **Standardized Logging**: Directs logs to `sys.stdout` (12-Factor App) for native `docker logs` capture without container disk space leakage.
