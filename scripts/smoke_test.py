"""
================================================================================
AI TICKET TRIAGE SYSTEM — END-TO-END SMOKE TEST SUITE
================================================================================
Usage:
Run this script to verify system health and test prediction functionality.

Execution:
    python scripts/smoke_test.py
================================================================================
"""

import json
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000"
HEALTH_URL = f"{BASE_URL}/health"
PREDICT_URL = f"{BASE_URL}/predict"

TIMEOUT_SECONDS = 60
POLL_INTERVAL = 3


def poll_health() -> bool:
    print(f"[INFO] Polling {HEALTH_URL} until model_loaded: true (Timeout: {TIMEOUT_SECONDS}s)...")
    start_time = time.time()

    while time.time() - start_time < TIMEOUT_SECONDS:
        try:
            req = urllib.request.Request(HEALTH_URL)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    print(f"  -> Health probe response: {data}")
                    if data.get("model_loaded") is True:
                        print("[SUCCESS] API is HEALTHY and ML Model is successfully loaded in memory!")
                        return True
        except urllib.error.URLError as err:
            print(f"  -> Waiting for API connection... ({err.reason})")
        except Exception as exc:
            print(f"  -> Waiting... ({exc})")

        time.sleep(POLL_INTERVAL)

    print("[ERROR] Timeout reached while waiting for ML model to load.")
    return False


def test_prediction() -> bool:
    print(f"\n[INFO] Sending sample POST request to {PREDICT_URL}...")

    payload = {
        "subject": "Billing issue regarding unauthorized recurring subscription charge",
        "description": "I observed a charge of $49.99 on my bank statement for a subscription I canceled last month. Please issue a refund.",
    }

    json_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        PREDICT_URL,
        data=json_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.status
            body = response.read().decode("utf-8")
            result = json.loads(body)

            print(f"  -> HTTP Status Code: {status_code}")
            print(f"  -> Response Payload:\n{json.dumps(result, indent=2)}")

            # Validate prediction fields (Queue, Ticket Type, Priority, Confidence)
            if status_code == 200 and "queue" in result and "ticket_type" in result and "priority" in result and "confidence" in result:
                print("\n=======================================================")
                print("  PASS: END-TO-END PIPELINE SMOKE TEST PASSED!        ")
                print("=======================================================\n")
                return True
            else:
                print("\n[FAIL] Unexpected response payload format returned.")
                return False

    except urllib.error.HTTPError as http_err:
        error_body = http_err.read().decode("utf-8")
        print(f"[FAIL] HTTP Error {http_err.code}: {error_body}")
        return False
    except Exception as exc:
        print(f"[FAIL] Exception during prediction test: {exc}")
        return False


def main():
    print("=======================================================")
    print("      AI TICKET TRIAGE SYSTEM — SMOKE TEST SUITE       ")
    print("=======================================================")

    if not poll_health():
        print("\n[FAIL] System Health Probe Failed.")
        sys.exit(1)

    if not test_prediction():
        print("\n[FAIL] Prediction Endpoint Test Failed.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
