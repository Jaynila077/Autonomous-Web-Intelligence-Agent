# restart_test_part1.py
import json
import sys
import time
import requests

BASE_URL = "http://localhost:8000"


def run_part1():
    print("\n" + "=" * 60)
    print("  PHASE 4 SERVER RESTART TEST — PART 1 (SUBMIT & HANDOFF)")
    print("=" * 60)

    # 1. Health check
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=3)
        if r.status_code != 200:
            print(f"[FAIL] Server health check returned {r.status_code}")
            sys.exit(1)
    except requests.RequestException as e:
        print(f"[FAIL] Could not connect to server at {BASE_URL}: {e}")
        sys.exit(1)
    print("[PASS] FastAPI server is reachable.")

    # 2. Register fresh user
    user_email = f"restart_test_{int(time.time())}@example.com"
    reg_resp = requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": user_email, "password": "password123"},
        timeout=5,
    )
    if reg_resp.status_code != 201:
        print(f"[FAIL] Registration failed: {reg_resp.text}")
        sys.exit(1)

    token_data = reg_resp.json()
    token = token_data["access_token"]
    user_id = token_data["user_id"]
    print(f"[PASS] Registered user '{user_id}'.")

    # 3. Submit query
    headers = {"Authorization": f"Bearer {token}"}
    sub_resp = requests.post(
        f"{BASE_URL}/api/v1/queries/",
        json={"query": "Testing server restart resilience during queue execution"},
        headers=headers,
        timeout=5,
    )
    if sub_resp.status_code != 202:
        print(f"[FAIL] Query submission failed ({sub_resp.status_code}): {sub_resp.text}")
        sys.exit(1)

    job_data = sub_resp.json()
    job_id = job_data["job_id"]
    stream_url = job_data["status_stream_url"]
    print(f"[PASS] Job enqueued successfully. Job ID: {job_id}")

    # 4. Stream until status reaches RESEARCHING
    sse_url = f"{BASE_URL}{stream_url}?token={token}"
    print(f"[*] Waiting for job to transition to RESEARCHING state...")

    started_executing = False
    start_time = time.time()

    with requests.get(sse_url, stream=True, timeout=15) as resp:
        if resp.status_code != 200:
            print(f"[FAIL] SSE stream returned {resp.status_code}: {resp.text}")
            sys.exit(1)

        for line in resp.iter_lines():
            if time.time() - start_time > 10:
                print("\n[FAIL] Timeout waiting for worker to pick up job. Is the arq worker running?")
                sys.exit(1)

            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data:"):
                    payload = json.loads(decoded.replace("data:", "").strip())
                    status = payload.get("status")
                    agent = payload.get("current_agent")
                    print(f"  [SSE Event] Status: {status} | Agent: {agent}")

                    if status in ("RESEARCHING", "VERIFYING", "REPORTING", "COMPLETED"):
                        started_executing = True
                        break

    if not started_executing:
        print("[FAIL] Job did not start execution.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  PART 1 COMPLETE — WORKER IS CURRENTLY PROCESSING THIS JOB")
    print("=" * 60)
    print(f"JOB_ID: {job_id}")
    print(f"TOKEN:  {token}")
    print("\nINSTRUCTIONS FOR RESTART TEST:")
    print("1. Go to Terminal 3 (FastAPI server) and press Ctrl+C to STOP Uvicorn.")
    print("2. Immediately START Uvicorn again in Terminal 3.")
    print("3. Run Part 2 with the parameters printed below:")
    print(f"\n   python restart_test_part2.py {job_id} {token}\n")


if __name__ == "__main__":
    run_part1()