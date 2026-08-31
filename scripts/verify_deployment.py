#!/usr/bin/env python3
"""
BHIV Rajya Enforcement Gateway — Deployment Verification Suite
Validates container health, core API contracts, and JWKS endpoints.
"""

import sys
import json
import argparse
import urllib.request
import urllib.error

def check_endpoint(name: str, url: str, method: str = "GET", payload: dict = None, expected_status: int = 200) -> bool:
    print(f"[*] Testing {name} -> {url} ({method})...", end=" ")
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    if payload:
        req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            if status == expected_status:
                print("✅ PASSED")
                try:
                    parsed = json.loads(body)
                    print(f"    Response: {json.dumps(parsed, indent=2)[:300]}...")
                except Exception:
                    print(f"    Raw: {body[:150]}")
                return True
            else:
                print(f"❌ FAILED (Status: {status}, Expected: {expected_status})")
                return False
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}: {e.reason}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Verify Rajya Deployment Health & Endpoints")
    parser.add_argument("--base-url", default="http://localhost:8015", help="Base URL of deployed service")
    args = parser.parse_args()
    
    base_url = args.base_url.rstrip("/")
    print("=" * 65)
    print(f"🔍 VERIFYING RAJYA DEPLOYMENT: {base_url}")
    print("=" * 65)
    
    results = []
    
    # 1. Health Probe
    results.append(check_endpoint("Health Check", f"{base_url}/health", method="GET"))
    
    # 2. JWKS Endpoint
    results.append(check_endpoint("JWKS Endpoint", f"{base_url}/.well-known/jwks.json", method="GET"))
    
    # 3. Text Risk Analysis Endpoint
    analyze_payload = {
        "text": "Normal operations query for telemetry check",
        "strict_mode": False
    }
    results.append(check_endpoint("Risk Scoring (/analyze)", f"{base_url}/analyze", method="POST", payload=analyze_payload))
    
    # 4. Rajya Validation Endpoint
    validation_payload = {
        "execution_id": "verify-run-001",
        "actor": "system_verifier",
        "action": "QUERY_TELEMETRY",
        "risk_score": 0.05,
        "confidence": 0.95
    }
    results.append(check_endpoint("Rajya Governance Validate", f"{base_url}/api/v1/rajya/validate", method="POST", payload=validation_payload))
    
    print("=" * 65)
    passed = sum(results)
    total = len(results)
    print(f"SUMMARY: {passed}/{total} checks passed.")
    
    if passed == total:
        print("🎉 ALL CHECKS PASSED — DEPLOYMENT CERTIFIED HEALTHY")
        sys.exit(0)
    else:
        print("⚠️ SOME CHECKS FAILED — REVIEW CONTAINER LOGS")
        sys.exit(1)

if __name__ == "__main__":
    main()
