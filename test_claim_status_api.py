"""Test script for claim status API endpoint."""

import json
import requests

# API endpoint
url = "http://localhost:8000/claim-status"

# Test request matching input_claim_status.json format
test_request = {
    "request_id": 201,
    "payer_name": "AETNA (COMMERCIAL & MEDICARE)",
    "payer_claim_id": None,
    "provider_claim_id": "818743774",
    "member_id": "W232596158",
    "patient_last_name": "URBAN",
    "patient_first_name": "IRELIN",
    "patient_dob": "2004-09-21",
    "subscriber_last_name": "URBAN",
    "subscriber_first_name": "IRELIN",
    "subscriber_same_as_patient": True,
    "provider_npi": "1346236833",
    "dos_from": "2025-06-27",
    "dos_to": "2025-06-27",
    "claim_amount": None
}

print("=" * 60)
print("Testing Claim Status API")
print("=" * 60)
print(f"URL: {url}")
print(f"Request: {json.dumps(test_request, indent=2)}")
print("=" * 60)
print()

try:
    response = requests.post(
        url,
        json=test_request,
        headers={"Content-Type": "application/json"},
        timeout=300  # 5 minutes timeout for bot processing
    )
    
    print(f"Status Code: {response.status_code}")
    print()
    
    if response.status_code == 200:
        result = response.json()
        print("[SUCCESS]")
        print(json.dumps(result, indent=2))
    else:
        print("[ERROR]")
        print(f"Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("[ERROR] Could not connect to API server")
    print("Make sure the server is running:")
    print("  python run_api.py")
except requests.exceptions.Timeout:
    print("[ERROR] Request timed out")
    print("The bot is still processing. Check server logs.")
except Exception as e:
    print(f"[ERROR] {e}")

