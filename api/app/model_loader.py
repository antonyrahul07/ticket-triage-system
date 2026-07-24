"""
ML Model Loader module for AI Customer Support Ticket Triage.

================================================================================
MEMBER 1 INTEGRATION SUPPORT:
================================================================================
Integrated with Member 1's multi-model directory structure:
1. Queue Model: `ticket_queue_model.joblib` or `model.joblib`
2. Type Model: `model.pkl` + `vectorizer.pkl` (Member 1 Type Classifier)
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.config import get_settings
from app.logger import get_logger

logger = get_logger("app.model_loader")


class ModelLoadError(Exception):
    """Base exception for model loading and initialization failures."""
    pass


class ModelNotFoundError(ModelLoadError):
    """Raised specifically when the model artifact is missing on disk."""
    pass


class ModelLoader:
    """
    Singleton manager for loading Member 1's Queue & Type models and executing inference.
    """

    FALLBACK_LABEL_MAP: dict[int, str] = {
        0: "Technical",
        1: "Billing",
        2: "Account",
        3: "General",
    }

    def __init__(self, model_path: str | Path | None = None) -> None:
        settings = get_settings()
        target_path = Path(model_path or settings.MODEL_PATH)
        
        # Support directory or direct file path resolution
        if target_path.is_dir():
            self.models_dir = target_path
            self.queue_model_path = target_path / "ticket_queue_model.joblib"
        else:
            self.models_dir = target_path.parent
            self.queue_model_path = target_path

        # Check alternative ticket_queue_model.joblib filename from Member 1
        alt_queue_path = self.models_dir / "ticket_queue_model.joblib"
        if alt_queue_path.exists():
            self.queue_model_path = alt_queue_path

        self.type_model_path: Path = self.models_dir / "model.pkl"
        self.vectorizer_path: Path = self.models_dir / "vectorizer.pkl"

        self._queue_model: Any = None
        self._type_model: Any = None
        self._type_vectorizer: Any = None

    @property
    def is_loaded(self) -> bool:
        """Returns True if at least the Queue model artifact is loaded in memory."""
        return self._queue_model is not None

    def load(self) -> None:
        """
        Loads Member 1's Queue Model and Type Model artifacts from disk into memory.
        """
        if self.is_loaded:
            return

        # 1. Load Queue Model (ticket_queue_model.joblib or model.joblib)
        if not self.queue_model_path.exists():
            raise ModelNotFoundError(
                f"Queue model artifact file not found at '{self.queue_model_path}'. "
                "Ensure Member 1's ticket_queue_model.joblib or model.joblib is saved in the models/ directory."
            )

        try:
            self._queue_model = joblib.load(self.queue_model_path)
            logger.info(f"Successfully loaded Queue model from '{self.queue_model_path}'.")
        except FileNotFoundError as fnf_err:
            raise ModelNotFoundError(
                f"Queue model artifact file not found at '{self.queue_model_path}'."
            ) from fnf_err
        except Exception as exc:
            raise ModelLoadError(
                f"Failed to deserialize Queue model at '{self.queue_model_path}': {str(exc)}"
            ) from exc

        # 2. Load Type Model & Vectorizer if present (Member 1 Type Classifier)
        if self.type_model_path.exists() and self.vectorizer_path.exists():
            try:
                self._type_model = joblib.load(self.type_model_path)
                self._type_vectorizer = joblib.load(self.vectorizer_path)
                logger.info(f"Successfully loaded Member 1 Type model & vectorizer from '{self.models_dir}'.")
            except Exception as exc:
                logger.warning(f"Could not load Type model/vectorizer ({exc}). Fallback to default ticket_type.")

    def predict(self, subject: str, description: str) -> dict[str, Any]:
        """
        Executes ML classification on ticket text for both Queue and Type.
        """
        if not self.is_loaded:
            self.load()

        combined_text = f"{subject.strip()} {description.strip()}"
        input_data = [combined_text]

        raw_queue_pred: Any = "General"
        raw_type_pred: Any = "Request"
        raw_priority_pred: Any = None
        confidence: float = 1.0

        # --- Queue Model Prediction ---
        artifact = self._queue_model

        if isinstance(artifact, dict):
            q_model = artifact.get("queue_model") or artifact.get("model") or artifact.get("classifier")
            p_model = artifact.get("priority_model")

            if q_model is not None:
                queue_preds = q_model.predict(input_data)
                raw_queue_pred = queue_preds[0]

                if hasattr(q_model, "predict_proba"):
                    probs = q_model.predict_proba(input_data)[0]
                    confidence = float(np.max(probs))

            if p_model is not None:
                p_preds = p_model.predict(input_data)
                raw_priority_pred = p_preds[0]

        else:
            queue_preds = artifact.predict(input_data)
            raw_queue_pred = queue_preds[0]

            if hasattr(artifact, "predict_proba"):
                probs = artifact.predict_proba(input_data)[0]
                confidence = float(np.max(probabilities := artifact.predict_proba(input_data)[0]))

        # --- Type Model Prediction (Member 1 Type Classifier) ---
        if self._type_model is not None and self._type_vectorizer is not None:
            try:
                vec_features = self._type_vectorizer.transform(input_data)
                type_preds = self._type_model.predict(vec_features)
                raw_type_pred = type_preds[0]
            except Exception as exc:
                logger.warning(f"Member 1 Type model inference failed: {exc}")

        # Decode Queue label
        queue_str = self._decode_label(raw_queue_pred, artifact)
        ticket_type_str = str(raw_type_pred)

        # Decode Priority label or calculate heuristic
        if raw_priority_pred is not None:
            priority_str = self._decode_label(raw_priority_pred, artifact, key="priority_label_encoder")
        else:
            priority_str = self._calculate_heuristic_priority(queue_str, confidence)

        logger.info(
            f"[PREDICTION] Queue: '{queue_str}' | Type: '{ticket_type_str}' | Priority: '{priority_str}' | Confidence: {confidence:.4f}"
        )

        return {
            "queue": queue_str,
            "ticket_type": ticket_type_str,
            "priority": priority_str,
            "confidence": round(confidence, 4),
        }

    def _decode_label(self, raw_label: Any, artifact: Any, key: str = "label_encoder") -> str:
        """Decodes raw prediction output into a human-readable string label."""
        if isinstance(raw_label, str) and not raw_label.isdigit():
            return raw_label

        if isinstance(artifact, dict) and key in artifact:
            encoder = artifact[key]
            if hasattr(encoder, "inverse_transform"):
                try:
                    return str(encoder.inverse_transform([raw_label])[0])
                except Exception:
                    pass

        if isinstance(raw_label, (int, np.integer)):
            int_val = int(raw_label)
            if self.FALLBACK_LABEL_MAP and int_val in self.FALLBACK_LABEL_MAP:
                return self.FALLBACK_LABEL_MAP[int_val]

        return str(raw_label)

    @staticmethod
    def _calculate_heuristic_priority(queue: str, confidence: float) -> str:
        """Fallback heuristic priority assignment."""
        if queue in ["Billing", "Account"] or confidence < 0.60:
            return "High"
        elif queue == "Technical":
            return "Medium"
        return "Low"


@lru_cache
def get_model_loader() -> ModelLoader:
    """Factory function returning a cached singleton instance of ModelLoader."""
    return ModelLoader()
