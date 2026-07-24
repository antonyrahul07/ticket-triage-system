# AI Customer Support Ticket Triage System — Backend API

An enterprise-grade, containerized FastAPI backend for automated customer support ticket classification, priority assignment, and confidence scoring using `scikit-learn` ML pipelines.

---

## System Architecture

```
                        +-----------------------------+
                        |   triage_trainer (One-shot) |
                        |   - Reads ./data (:ro)      |
                        |   - Writes model.joblib     |
                        +--------------+--------------+
                                       |
                  (condition: service_completed_successfully)
                                       |
               +-----------------------+-----------------------+
               |                                               |
               v                                               v
  +----------------------------+             +----------------------------+
  |   triage_api (FastAPI)     |             | triage_evaluator(One-shot) |
  |   - Mounts models_data :ro |             | - Mounts models_data :ro   |
  |   - Port 8000:8000         |             | - Mounts ./data :ro        |
  |   - Healthcheck configured |             | - Writes ./evaluator/output|
  +----------------------------+             +----------------------------+
```

### End-to-End Request Lifecycle
`Client Request` → `FastAPI Route Handler` → `Pydantic Input Validation` → `Singleton ModelLoader Inference` → `Pydantic Response Serialization` → `Client Response`

---

## API Endpoints & Example Usage

### 1. Root Welcome Endpoint
- **URL**: `GET /`
- **Description**: Returns basic service metadata and interactive OpenAPI documentation pointers.
- **cURL Command**:
  ```bash
  curl -X GET http://localhost:8000/
  ```
- **Example Response** (`200 OK`):
  ```json
  {
    "title": "AI Ticket Triage API",
    "version": "1.0.0",
    "message": "Welcome to the AI Ticket Triage System API.",
    "documentation": "/docs"
  }
  ```

### 2. Health & Readiness Probe
- **URL**: `GET /health`
- **Description**: Evaluates backend service operational status and ML model availability. Used by Docker `HEALTHCHECK` (returns `200 OK` regardless of model readiness).
- **cURL Command**:
  ```bash
  curl -X GET http://localhost:8000/health
  ```
- **Example Response (Healthy)** (`200 OK`):
  ```json
  {
    "status": "healthy",
    "model_loaded": true,
    "version": "1.0.0"
  }
  ```

### 3. Ticket Triage Prediction Endpoint
- **URL**: `POST /predict`
- **Description**: Accepts a support ticket payload (`subject` + `description`), runs TF-IDF vectorization and Logistic Regression inference, and returns department queue assignment, priority score, and confidence.
- **cURL Command**:
  ```bash
  curl -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{
      "subject": "Cannot log into my account after password reset",
      "description": "I clicked the reset link in my email, but my credentials still fail on login."
    }'
  ```
- **Example Response** (`200 OK`):
  ```json
  {
    "queue": "Account",
    "priority": "High",
    "confidence": 0.9412,
    "status": "success"
  }
  ```

### 4. On-Demand Model Reload (Convenience Endpoint)
- **URL**: `POST /reload-model`
- **Description**: Re-triggers model artifact deserialization without restarting the API container.
- **cURL Command**:
  ```bash
  curl -X POST http://localhost:8000/reload-model
  ```

---

## Running with Docker Compose

To build and launch all 3 microservices concurrently:
```bash
docker compose up --build
```

### Service Boot Order:
1. **`triage_trainer`**: Boots first, trains the ML pipeline on `./data`, outputs `model.joblib` to shared volume `models_data`, and exits cleanly (`exit 0`).
2. **`triage_api` & `triage_evaluator`**: Wait for `trainer` to complete via `depends_on: condition: service_completed_successfully`, then boot in parallel.

### Monitoring & Verification
- **Check container status**: `docker compose ps`
- **Stream API logs**: `docker compose logs -f api`
- **Verify health**: `curl http://localhost:8000/health`
- **Run Smoke Test Suite**: `python scripts/smoke_test.py`

---

## Troubleshooting Guide

### Issue 1: `/predict` returns `503 Service Unavailable`
- **Root Cause**: `model.joblib` is missing or the trainer container is still processing.
- **Resolution**:
  1. Inspect trainer logs: `docker compose logs trainer`
  2. Verify `model.joblib` exists in `models_data`.
  3. Once generated, call `curl -X POST http://localhost:8000/reload-model` to load the artifact into memory without restarting the API container.

### Issue 2: `ModelLoadError` due to artifact shape mismatch
- **Root Cause**: Member 1 produced a `dict` artifact or single `Pipeline` object with customized dictionary key names.
- **Resolution**: `model_loader.py` dynamically handles both single estimators and `dict` shapes (`{"queue_model": ..., "priority_model": ...}`). Check dictionary keys in `model_loader.py` to ensure they match Member 1's export schema.

---

## Hackathon Judge Q&A Cheat Sheet

| Question | Architectural Answer for Judges |
| :--- | :--- |
| **Why use a shared volume instead of copying `model.joblib` into the API Docker image?** | **Decoupling and Image Immutability**: Copying model binaries into the Dockerfile bakes weights into the image, requiring full image rebuilds & redeployments every time the ML model is retrained. Using a shared Docker volume decouples MLOps (training) from DevOps (API infrastructure). The API image is compiled once and stays static. |
| **Why does the API not crash if the model artifact isn't loaded yet?** | **High Availability & Fault Tolerance**: Crashing container loops (CrashLoopBackOff) disrupt API routing and health probes. By catching `ModelNotFoundError`, the API boots cleanly in `degraded` mode, serving `/health` probes while returning informative HTTP 503 errors on `/predict` until the trainer completes. |
| **Why use a non-root user (`appuser`) in the Dockerfile?** | **Container Security (Least Privilege)**: Running container processes as root violates security best practices. If an unhandled RCE vulnerability is exploited in a dependency, a non-root user restricts the attacker from privilege escalation or host filesystem access. |
| **How does `depends_on: condition: service_completed_successfully` work?** | **Job Lifecycle Synchronization**: Standard `depends_on` only waits for a dependent container to *start*. `service_completed_successfully` (Compose v2+) explicitly blocks `api` startup until the `trainer` batch job finishes execution and exits with status code 0. |
| **How would you scale this to multiple API replicas in production?** | **Horizontal Pod Autoscaling**: Because `ModelLoader` is a stateless singleton that reads `model.joblib` as a read-only volume mount, we can easily scale out to *N* API replicas behind an NGINX load balancer or Kubernetes HPA with zero state synchronization issues. |
