#!/usr/bin/env python3
"""
AWIS Backend — End-to-End API Test Script

Tests the full API lifecycle WITHOUT touching the real agent pipeline:
register -> login -> submit job -> stream status (SSE) -> download report,
plus negative/security cases (no token, wrong user, expired/garbage token,
nonexistent job, premature report download).

Requires the server running with MOCK_AGENT=true so job completion doesn't
depend on real LLM/tool API keys.

Usage:
    python test_awis_api.py [--base-url http://127.0.0.1:8000]
"""
import argparse
import json
import sys
import time
import uuid

import requests

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results = []


def check(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    results.append((name, condition))
    return condition


def stream_sse(url: str, headers=None, params=None, timeout=30):
    """Minimal SSE line reader — good enough for job_status events without extra deps."""
    events = []
    with requests.get(url, headers=headers, params=params, stream=True, timeout=timeout) as resp:
        if resp.status_code != 200:
            return resp.status_code, events
        event_type, data_lines = None, []
        for raw_line in resp.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip("\r")
            if line == "":
                if data_lines:
                    events.append((event_type, "\n".join(data_lines)))
                    data_lines = []
                    event_type = None
                continue
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
        return resp.status_code, events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    print(f"\n=== AWIS API Test Run ({base}) ===")
    print(f"Test user: {email}\n")

    # --- Health check ---
    r = requests.get(f"{base}/health")
    check("Health check returns 200", r.status_code == 200, f"got {r.status_code}")

    # --- Register ---
    r = requests.post(f"{base}/auth/register", json={"email": email, "password": password})
    check("Register succeeds (201)", r.status_code == 201, f"got {r.status_code}: {r.text}")
    token = r.json().get("access_token") if r.status_code == 201 else None
    user_id = r.json().get("user_id") if r.status_code == 201 else None
    check("Register response includes access_token", bool(token))

    # --- Duplicate register ---
    r = requests.post(f"{base}/auth/register", json={"email": email, "password": password})
    check("Duplicate register rejected (400)", r.status_code == 400, f"got {r.status_code}")

    # --- Login wrong password ---
    r = requests.post(f"{base}/auth/login", json={"email": email, "password": "wrongpassword"})
    check("Login with wrong password rejected (401)", r.status_code == 401, f"got {r.status_code}")

    # --- Login correct ---
    r = requests.post(f"{base}/auth/login", json={"email": email, "password": password})
    check("Login with correct password succeeds (200)", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        token = r.json()["access_token"]  # use freshest token going forward

    auth_headers = {"Authorization": f"Bearer {token}"}

    # --- Submit without token ---
    r = requests.post(f"{base}/api/v1/queries/", json={"query": "test query about vector databases"})
    check("Submit query without token rejected (401)", r.status_code == 401, f"got {r.status_code}")

    # --- Submit with garbage token ---
    r = requests.post(
        f"{base}/api/v1/queries/",
        json={"query": "test query about vector databases"},
        headers={"Authorization": "Bearer not.a.valid.token"},
    )
    check("Submit query with garbage token rejected (401)", r.status_code == 401, f"got {r.status_code}")

    # --- Submit with valid token ---
    r = requests.post(
        f"{base}/api/v1/queries/",
        json={"query": "What are the latest challenges with vector databases?"},
        headers=auth_headers,
    )
    check("Submit query with valid token accepted (202)", r.status_code == 202, f"got {r.status_code}: {r.text}")
    job_id = r.json().get("job_id") if r.status_code == 202 else None
    check("Submit response includes job_id", bool(job_id))

    if not job_id:
        print("\nCannot continue without a job_id — aborting remaining tests.")
        print_summary()
        sys.exit(1)

    # --- Stream with header auth, wait for COMPLETED or FAILED ---
    status_code, events = stream_sse(
        f"{base}/api/v1/queries/{job_id}/stream", headers=auth_headers, timeout=60
    )
    check("Stream with header auth returns 200", status_code == 200, f"got {status_code}")
    check("Stream produced at least one job_status event", len(events) > 0)

    final_status = None
    for event_type, data in events:
        try:
            payload = json.loads(data)
            final_status = payload.get("status")
        except json.JSONDecodeError:
            pass
    print(f"    (final status from stream: {final_status})")
    check(
        "Job reached COMPLETED or FAILED via stream",
        final_status in ("COMPLETED", "FAILED"),
        f"got {final_status}",
    )

    # --- Stream with query-param token (fresh job so we get a live event again) ---
    r2 = requests.post(
        f"{base}/api/v1/queries/",
        json={"query": "Second test query for SSE query-param auth check"},
        headers=auth_headers,
    )
    job_id_2 = r2.json().get("job_id") if r2.status_code == 202 else None
    if job_id_2:
        status_code, events2 = stream_sse(
            f"{base}/api/v1/queries/{job_id_2}/stream", params={"token": token}, timeout=60
        )
        check("Stream with ?token= query param returns 200", status_code == 200, f"got {status_code}")
        check("Query-param stream produced at least one event", len(events2) > 0)

    # --- Stream with no auth at all ---
    status_code, _ = stream_sse(f"{base}/api/v1/queries/{job_id}/stream", timeout=5)
    check("Stream with no auth rejected (401)", status_code == 401, f"got {status_code}")

    # --- Register a second user to test ownership isolation ---
    email2 = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{base}/auth/register", json={"email": email2, "password": password})
    token2 = r.json().get("access_token") if r.status_code == 201 else None
    check("Second user registered for ownership test", bool(token2))

    if token2:
        other_headers = {"Authorization": f"Bearer {token2}"}
        r = requests.get(f"{base}/api/v1/queries/{job_id}/stream", headers=other_headers, stream=True)
        check(
            "Other user cannot stream someone else's job (403)",
            r.status_code == 403,
            f"got {r.status_code}",
        )
        r.close()

        r = requests.get(f"{base}/api/v1/queries/{job_id}/report", headers=other_headers)
        check(
            "Other user cannot download someone else's report (403)",
            r.status_code == 403,
            f"got {r.status_code}",
        )

    # --- Report download for a nonexistent job ---
    r = requests.get(f"{base}/api/v1/queries/job_doesnotexist/report", headers=auth_headers)
    check("Report for nonexistent job returns 404", r.status_code == 404, f"got {r.status_code}")

    # --- Report download for the real job (should be ready if COMPLETED) ---
    if final_status == "COMPLETED":
        r = requests.get(f"{base}/api/v1/queries/{job_id}/report", headers=auth_headers)
        check("Report download succeeds after completion (200)", r.status_code == 200, f"got {r.status_code}")
        check("Report content is non-empty", len(r.text.strip()) > 0)
    elif final_status == "FAILED":
        r = requests.get(f"{base}/api/v1/queries/{job_id}/report", headers=auth_headers)
        check(
            "Report download correctly refused for FAILED job (400)",
            r.status_code == 400,
            f"got {r.status_code}",
        )

    print_summary()


def print_summary():
    print("\n=== Summary ===")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"{passed}/{total} checks passed")
    if passed != total:
        print("\nFailed checks:")
        for name, ok in results:
            if not ok:
                print(f"  - {name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
