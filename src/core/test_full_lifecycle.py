# tests/test_full_lifecycle.py
import os
import time
import requests
import json

# Force MOCK_AGENT=true for quick testing
os.environ["MOCK_AGENT"] = "true"

BASE_URL = "http://localhost:8000"

def test_full_api_lifecycle():
    print("\n--- STARTING FULL API LIFECYCLE TEST (MOCK MODE) ---")

    # 1. Register User & Get JWT
    test_email = f"test_{int(time.time())}@example.com"
    reg_resp = requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": test_email, "password": "password123"},
    )
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    token_data = reg_resp.json()
    token = token_data["access_token"]
    user_id = token_data["user_id"]
    print(f"✔ Auth Success: User '{user_id}' registered and received JWT.")

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit Query
    query_payload = {"query": "Explain vector indexing performance trade-offs."}
    submit_resp = requests.post(f"{BASE_URL}/api/v1/queries/", json=query_payload, headers=headers)
    assert submit_resp.status_code == 202, f"Query submission failed: {submit_resp.text}"
    job_data = submit_resp.json()
    job_id = job_data["job_id"]
    stream_url = job_data["status_stream_url"]
    report_url = job_data["report_download_url"]
    print(f"✔ Query Enqueued: Job ID '{job_id}'. Status URL: {stream_url}")

    # 3. Stream Status via SSE using ?token= query parameter
    sse_url = f"{BASE_URL}{stream_url}?token={token}"
    print(f"Connecting to SSE stream: {sse_url}")

    with requests.get(sse_url, stream=True) as stream_resp:
        assert stream_resp.status_code == 200, f"SSE connection failed: {stream_resp.text}"
        completed = False
        for line in stream_resp.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data:"):
                    payload_str = decoded.replace("data:", "").strip()
                    payload = json.loads(payload_str)
                    current_status = payload["status"]
                    agent = payload.get("current_agent")
                    print(f"  [SSE Update] Status: {current_status} | Agent: {agent}")

                    if current_status == "COMPLETED":
                        completed = True
                        break

        assert completed, "Job failed to transition to COMPLETED state."
        print("✔ SSE Stream Success: Job reached COMPLETED status.")

    # 4. Fetch Completed Report
    report_resp = requests.get(f"{BASE_URL}{report_url}", headers=headers)
    assert report_resp.status_code == 200, f"Report download failed: {report_resp.text}"
    report_content = report_resp.text

    assert "# Mock Intelligence Brief" in report_content, "Unexpected report header!"
    print("✔ Report Download Success: Content verified on disk.")
    print("\n--- FULL API LIFECYCLE TEST PASSED SUCCESSFULLY ---")


if __name__ == "__main__":
    test_full_api_lifecycle()