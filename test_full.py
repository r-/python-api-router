"""Verbose test script for the API router and R.O.B.E.R.T. Agent bridge."""

import httpx
import json
import sys
import time

BASE = "http://127.0.0.1:8787"
TIMEOUT = 30.0

def main():
    print(f"STARTING verbose test against {BASE}")
    print(f"TIMEOUT set to {TIMEOUT} seconds")
    print("-" * 40)

    try:
        # 1. Health check
        print("STEP 1: Checking API health...")
        try:
            r = httpx.get(f"{BASE}/health", timeout=5.0)
            print(f"SUCCESS: Health check status: {r.status_code}")
        except httpx.RequestError as e:
            print(f"ERROR: Health check failed: {e}")
            sys.exit(1)

        print("-" * 40)

        # 2. Proxy request to OpenRouter
        print("STEP 2: Testing LLM Proxy...")
        payload_proxy = {
            "method": "POST",
            "path": "/chat/completions",
            "body": {
                "model": "google/gemini-2.0-flash-lite-001",
                "messages": [{"role": "user", "content": "Say 'Proxy OK'"}],
                "stream": False,
            },
        }
        
        start_time = time.time()
        r = httpx.post(
            f"{BASE}/proxy",
            headers={"Authorization": "Bearer rk-robot-1", "Content-Type": "application/json"},
            content=json.dumps(payload_proxy).encode("utf-8"),
            timeout=TIMEOUT,
        )
        print(f"RESPONSE: Status {r.status_code} in {time.time() - start_time:.2f}s")
        if r.status_code == 200:
            print(f"REPLY: {r.json()['choices'][0]['message']['content']}")

        print("-" * 40)

        # 3. Agent Bridge Request
        print("STEP 3: Testing R.O.B.E.R.T. Agent Bridge...")
        payload_agent = {
            "message": "Hello Robert, introduce yourself briefly in Swedish.",
            "session_key": "test-session-001"
        }
        
        start_time = time.time()
        r = httpx.post(
            f"{BASE}/agent",
            headers={"Authorization": "Bearer rk-robot-1", "Content-Type": "application/json"},
            content=json.dumps(payload_agent).encode("utf-8"),
            timeout=TIMEOUT,
        )
        print(f"RESPONSE: Status {r.status_code} in {time.time() - start_time:.2f}s")
        if r.status_code == 200:
            data = r.json()
            print(f"AGENT: {data['content']}")
            print(f"ITERATIONS: {data['iterations']}")
        else:
            print(f"ERROR: {r.text}")

    except Exception as e:
        print(f"CRASH: Unexpected error: {e}")
    
    print("-" * 40)
    print("FINISH: Test finished.")

if __name__ == "__main__":
    main()
