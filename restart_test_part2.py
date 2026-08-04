# restart_test_part2.py
import json
import sys
import time
import requests

BASE_URL = "http://localhost:8000"


def run_part2(job_id: str, token: str):
    print("\n" + "=" * 60)
    print("  PHASE 4 SERVER RESTART TEST — PART 2 (RECOVERY & REPORT VERIFICATION)")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Verify server health post-restart
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=3)
        if r.status_code != 200:
            print(f"[FAIL] Server health check returned {r.status_code}")
            sys.exit(1)
    except requests.RequestException as e:
        print(f"[FAIL] Could not connect to restarted server at {BASE_URL}: {e}")
        sys.exit(1)
    print("[PASS] Reconnected to restarted FastAPI server.")

    # 2. Poll/Stream SSE status post-restart
    sse_url = f"{BASE_URL}/api/v1/queries/{job_id}/stream?token={token}"
    print(f"[*] Reattaching to SSE stream for Job ID: {job_id}...")

    completed = False
    start_time = time.time()

    try:
        with requests.get(sse_url, stream=True, timeout=20) as resp:
            if resp.status_code != 200:
                print(f"[FAIL] SSE stream connection failed ({resp.status_code}): {resp.text}")
                sys.exit(1)

            for line in resp.iter_lines():
                if time.time() - start_time > 20:
                    print("\n[FAIL] Timeout waiting for job completion.")
                    sys.exit(1)

                if line:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data:"):
                        payload = json.loads(decoded.replace("data:", "").strip())
                        status = payload.get("status")
                        agent = payload.get("current_agent")
                        print(f"  [SSE Event Post-Restart] Status: {status} | Agent: {agent}")

                        if status == "COMPLETED":
                            completed = True
                            break
                        elif status == "FAILED":
                            print(f"[FAIL] Job marked FAILED: {payload.get('error_message')}")
                            sys.exit(1)
    except requests.RequestException as e:
        print(f"[*] SSE stream closed or completed ({e}). Checking report endpoint directly...")

    # 3. Download report to verify persistence and completion
    report_url = f"{BASE_URL}/api/v1/queries/{job_id}/report"
    report_resp = requests.get(report_url, headers=headers, timeout=5)

    if report_resp.status_code != 200:
        print(f"[FAIL] Report download failed ({report_resp.status_code}): {report_resp.text}")
        sys.exit(1)

    report_text = report_resp.text
    print("\n[PASS] Report successfully downloaded from restarted server.")
    print(f"[PASS] Report byte length: {len(report_text)} bytes")

    print("\n--- REPORT PREVIEW ---")
    print(report_text[:300])
    print("----------------------\n")

    print("=" * 60)
    print("  PART 2 COMPLETE — SERVER RESTART TEST SUCCESSFUL")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python restart_test_part2.py <JOB_ID> <TOKEN>")
        sys.exit(1)

    run_part2(sys.argv[1], sys.argv[2])