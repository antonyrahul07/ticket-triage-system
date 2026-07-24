"""
ML Model Artifact Inspection Script.

Usage:
    python scripts/inspect_model.py <path_to_model.joblib>
"""

import sys
from pathlib import Path
import joblib


def inspect_model(model_path: str) -> None:
    path = Path(model_path)
    if not path.exists():
        print(f"[ERROR] Model file not found at '{path}'")
        sys.exit(1)

    print("=======================================================")
    print(f"       INSPECTING MODEL ARTIFACT: {path.name}")
    print("=======================================================")

    try:
        obj = joblib.load(path)
    except Exception as exc:
        print(f"[ERROR] Failed to deserialize joblib file: {exc}")
        sys.exit(1)

    obj_type = f"{type(obj).__module__}.{type(obj).__name__}"
    print(f"Top-Level Object Type: {obj_type}\n")

    # 1. Dictionary Artifact Inspection
    if isinstance(obj, dict):
        print("--- Dictionary Keys & Values ---")
        for key, val in obj.items():
            val_type = f"{type(val).__module__}.{type(val).__name__}"
            print(f"  Key: '{key}' -> Type: {val_type}")
            if hasattr(val, "classes_"):
                print(f"       classes_: {getattr(val, 'classes_')}")
            if hasattr(val, "named_steps"):
                print(f"       Pipeline steps: {list(val.named_steps.keys())}")
        print()

    # 2. Pipeline Object Inspection
    elif hasattr(obj, "named_steps"):
        print("--- scikit-learn Pipeline Steps ---")
        for step_name, step_obj in obj.named_steps.items():
            print(f"  Step: '{step_name}' -> Class: {type(step_obj).__name__}")
        print()

    # 3. Capability Probes
    print("--- Model Capabilities & Attributes ---")
    has_predict_proba = hasattr(obj, "predict_proba") or (
        isinstance(obj, dict) and any(hasattr(v, "predict_proba") for v in obj.values())
    )
    print(f"  hasattr('predict_proba'): {has_predict_proba}")

    if hasattr(obj, "classes_"):
        print(f"  classes_: {obj.classes_}")

    # 4. Sample Test Prediction
    print("\n--- Running Sample Test Inference ---")
    sample_text = ["Cannot log into my user account after password reset"]
    try:
        if isinstance(obj, dict):
            model_inst = obj.get("queue_model") or obj.get("model") or obj.get("classifier")
            if model_inst and hasattr(model_inst, "predict"):
                pred = model_inst.predict(sample_text)
                print(f"  Sample Raw Prediction: {pred} (type: {type(pred[0]).__name__})")
                if hasattr(model_inst, "predict_proba"):
                    probs = model_inst.predict_proba(sample_text)
                    print(f"  Sample Probabilities: {probs}")
        elif hasattr(obj, "predict"):
            pred = obj.predict(sample_text)
            print(f"  Sample Raw Prediction: {pred} (type: {type(pred[0]).__name__})")
            if hasattr(obj, "predict_proba"):
                probs = obj.predict_proba(sample_text)
                print(f"  Sample Probabilities: {probs}")
    except Exception as exc:
        print(f"  [NOTE] Test inference execution note: {exc}")

    print("=======================================================")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/inspect_model.py <path_to_model.joblib>")
        sys.exit(1)
    inspect_model(sys.argv[1])
