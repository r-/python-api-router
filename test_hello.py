"""Verbose test script for the API router with timeout (No Emojis for Windows compatibility)."""

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
        start_time = time.time()
        try:
            r = httpx.get(f"{BASE}/health", timeout=5.0)
            elapsed = time.time() - start_time
            print(f"SUCCESS: Health check status: {r.status_code} ({elapsed:.2f}s)")
            print(f"BODY: {r.text}")
        except httpx.RequestError as e:
            print(f"ERROR: Health check failed: {e}")
            sys.exit(1)

        print("-" * 40)

        # 2. Proxy request to OpenRouter
        print("STEP 2: Sending proxy request to OpenRouter...")
        payload = {
            "method": "POST",
            "path": "/chat/completions",
            "body": {
                "model": "google/gemini-2.0-flash-001",
                "messages": [{"role": "user", "content": "Say hello in Swedish!"}],
                "stream": False,
            },
        }
        
        headers = {
            "Authorization": "Bearer rk-robot-1",
            "Content-Type": "application/json; charset=utf-8",
        }

        print(f"PAYLOAD: {json.dumps(payload, indent=2)}")
        print(f"AUTH: Using policy rk-robot-1")
        
        start_time = time.time()
        try:
            r = httpx.post(
                f"{BASE}/proxy",
                headers=headers,
                content=json.dumps(payload).encode("utf-8"),
                timeout=TIMEOUT,
            )
            elapsed = time.time() - start_time
            print(f"RESPONSE: Received in {elapsed:.2f}s")
            print(f"STATUS: {r.status_code}")

            if r.status_code == 200:
                data = r.json()
                print("DONE: Request successful!")
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"MODEL:  {data.get('model', '?')}")
                print(f"REPLY:  {content}")
            else:
                print(f"WARNING: Proxy returned an error:")
                print(f"DETAILS: {r.text}")
                
        except httpx.TimeoutException:
            print(f"STOP: Request timed out after {TIMEOUT} seconds.")
        except httpx.RequestError as e:
            print(f"ERROR: Request failed: {e}")

    except Exception as e:
        print(f"CRASH: Unexpected error: {e}")
    
    print("-" * 40)
    print("FINISH: Test finished.")

if __name__ == "__main__":
    main()
