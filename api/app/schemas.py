from pydantic import BaseModel, ConfigDict, Field


class TicketRequest(BaseModel):
    """
    Data validation schema for incoming customer support ticket requests.
    """

    subject: str = Field(
        ...,
        min_length=1,
        description="The subject line or brief summary of the customer support ticket.",
        json_schema_extra={"example": "Cannot log into my account after password reset"},
    )
    description: str = Field(
        ...,
        min_length=1,
        description="The full detailed description of the customer issue.",
        json_schema_extra={"example": "I tried resetting my password using the email link, but I still get an invalid credentials error when logging in."},
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subject": "Cannot log into my account after password reset",
                "description": "I tried resetting my password using the email link, but I still get an invalid credentials error when logging in."
            }
        }
    )


class PredictionResponse(BaseModel):
    """
    Data serialization schema for Member 1's ML model triage predictions.
    Supports both Queue classification and Type classification models.
    """

    queue: str = Field(
        ...,
        description="Target support queue category predicted by Member 1's queue model.",
        json_schema_extra={"example": "Account"},
    )
    ticket_type: str = Field(
        default="Request",
        description="Ticket category type predicted by Member 1's type model.",
        json_schema_extra={"example": "Incident"},
    )
    priority: str = Field(
        ...,
        description="Calculated urgency/priority score for ticket resolution (e.g. High, Medium, Low).",
        json_schema_extra={"example": "High"},
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence probability score of the prediction, ranging from 0.0 to 1.0.",
        json_schema_extra={"example": 0.94},
    )
    status: str = Field(
        default="success",
        description="Response execution status indicator.",
        json_schema_extra={"example": "success"},
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "queue": "Account",
                "ticket_type": "Incident",
                "priority": "High",
                "confidence": 0.94,
                "status": "success"
            }
        }
    )


class HealthResponse(BaseModel):
    """
    Schema for backend service and ML model health check probes.
    """

    status: str = Field(
        ...,
        description="Current operational status of the service (e.g. 'ok', 'unhealthy').",
        json_schema_extra={"example": "ok"},
    )
    model_loaded: bool = Field(
        ...,
        description="Boolean flag indicating whether the ML model artifact is loaded in memory.",
        json_schema_extra={"example": True},
    )
    version: str = Field(
        ...,
        description="Current API software version.",
        json_schema_extra={"example": "1.0.0"},
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "model_loaded": True,
                "version": "1.0.0"
            }
        }
    )


class ErrorResponse(BaseModel):
    """
    Standardized error payload schema for API exception handling.
    """

    status: str = Field(
        default="error",
        description="Static status indicator set to 'error'.",
        json_schema_extra={"example": "error"},
    )
    message: str = Field(
        ...,
        description="High-level human-readable error summary.",
        json_schema_extra={"example": "Model artifact not found"},
    )
    detail: str | None = Field(
        default=None,
        description="Optional detailed traceback or contextual diagnostic info.",
        json_schema_extra={"example": "Failed to load model file from path /app/models/model.joblib"},
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "error",
                "message": "Model artifact not found",
                "detail": "Failed to load model file from path /app/models/model.joblib"
            }
        }
    )
