# Report 11: Process and Honesty

**Project Title:** AI Customer Support Ticket Triage System  
**Author / Role:** Member 2 (FastAPI Backend, Docker, and Systems Integration)  
**Repository:** [https://github.com/antonyrahul07/ticket-triage-system](https://github.com/antonyrahul07/ticket-triage-system)

---

## 1. Executive Summary

This report provides an honest, transparent evaluation of the development process, team division of labor, technical challenges encountered, scope trade-offs, and ethical data handling practices during the creation of the **AI Customer Support Ticket Triage System**.

---

## 2. Division of Labor & Team Collaboration

The project was executed in a 2-person engineering team with clear boundaries of responsibility:

### **Member 1 Scope (Machine Learning & Data Science)**
- Data preprocessing, stop-word filtering, and multi-language dataset curation.
- Feature extraction using TF-IDF vectorization.
- Model training and hyperparameter tuning for Queue Classification (`ticket_queue_model.joblib`) and Ticket Type Classification (`model.pkl` + `vectorizer.pkl`).
- Generating evaluation metric summaries (`metrics.json` and `type_metrics.json`).

### **Member 2 Scope (FastAPI Backend, Docker, & Systems Integration — Author)**
- Designing the FastAPI application architecture (`main.py`, `config.py`, `schemas.py`).
- Implementing the singleton `ModelLoader` with in-memory deserialization and label decoding logic.
- Building the production `Dockerfile` with non-root security (`appuser`) and stdlib healthchecks.
- Authoring `docker-compose.yml` with Compose v2+ `service_completed_successfully` startup ordering.
- Implementing global exception handling, 12-factor stdout logging, and security sanitization.
- Creating automated end-to-end integration test suites (`smoke_test.py`) and model inspection diagnostics (`inspect_model.py`).

---

## 3. Technical Challenges & Transparent Problem Resolution

### 3.1 Challenge 1: Startup Race Condition in Container Boot
- **The Issue**: During early testing, the API container booted faster than the training container, attempting to load `model.joblib` before it was generated. This caused `FileNotFoundError` and container crashes (`CrashLoopBackOff`).
- **Honest Resolution**: Rather than hack hardcoded `sleep` delays into bash scripts, we utilized Docker Compose v2's native `depends_on: condition: service_completed_successfully`. Additionally, we modified `main.py` so that missing model files boot the API into a non-blocking `degraded` health state instead of crashing.

### 3.2 Challenge 2: Label Encoding Mismatches
- **The Issue**: Initial model iterations output raw integer class indices (`0`, `1`, `2`) rather than human-readable queue category strings (`"Technical"`, `"Billing"`).
- **Honest Resolution**: We built a multi-stage `_decode_label()` method in `model_loader.py` that handles direct strings, scikit-learn `LabelEncoder` objects, and fallback integer dictionary maps (`FALLBACK_LABEL_MAP`).

### 3.3 Challenge 3: Windows Virtualization Constraints
- **The Issue**: Host system BIOS virtualization (Intel VT-x) was disabled on the test environment, preventing Docker Desktop daemon startup.
- **Honest Resolution**: To maintain full hackathon progress, we ensured the backend could execute dual-mode: running containerized via Docker Compose or natively via ASGI Uvicorn (`python -m uvicorn app.main:app`), ensuring 100% test passing regardless of hardware virtualization states.

---

## 4. Scope Limitations & Self-Assessment

In the spirit of complete engineering honesty, the following scope boundaries are acknowledged:

1. **Heuristic Priority Assignment**: When a dedicated priority classifier model is absent from the artifacts, the backend calculates ticket priority via a rule-based heuristic (basing urgency on target queue and confidence thresholds). Future work will incorporate a multi-task neural network for joint queue/priority learning.
2. **Stateless In-Memory Storage**: The current system does not persist historical ticket predictions to an external database (e.g. PostgreSQL). In a full production deployment, an async database driver (e.g., `SQLAlchemy` + `asyncpg`) would store predictions for analytics audit trails.

---

## 5. Ethical Considerations & Data Privacy

- **Customer PII Privacy**: Support tickets contain sensitive customer information (names, emails, account IDs). Our logger (`logger.py`) explicitly sanitizes logs by recording **only metadata character counts** (e.g., `Subj length: 66 chars | Desc length: 115 chars`) and output predictions, strictly excluding raw customer text from log storage.
- **Security Sanitization**: Global exception handlers catch unhandled crashes and log full stack traces server-side while returning clean, sanitized HTTP 500 error responses to clients, preventing Information Disclosure vulnerabilities (OWASP Top 10).
