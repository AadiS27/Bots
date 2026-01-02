# API Testing Guide

## Starting the Server

1. Make sure you're in the project root directory
2. Run: `python run_api.py`
3. Server will start at `http://localhost:8000`

## Testing Claim Status

### Using curl:
```bash
curl --request POST \
  --url "http://localhost:8000/claim-status" \
  --header "Authorization: YOUR_TOKEN" \
  --header "Content-Type: application/json" \
  --data '{
    "tradingPartnerServiceId": "60054",
    "controlNumber": "818743774",
    "encounter": {
      "beginningDateOfService": "20250627",
      "endDateOfService": "20250627"
    },
    "providers": [
      {
        "npi": "1346236833",
        "organizationName": "PEDIATRIC CARE SPECIALISTS",
        "providerType": "BillingProvider"
      }
    ],
    "subscriber": {
      "dateOfBirth": "20040921",
      "firstName": "IRELIN",
      "lastName": "URBAN",
      "memberId": "W232596158"
    }
  }'
```

### Using Python:
```bash
python test_claim_status_api.py
```

## Important Notes

- **Restart the server** after making code changes
- The server automatically routes to the correct bot based on the endpoint:
  - `/claim-status` → ClaimStatusBot
  - `/claims` → ClaimsBot  
  - `/eligibility` → EligibilityBot
- Date format: Input should be `YYYYMMDD`, output is `YYYY-MM-DD`
- The `tradingPartnerServiceId` may need to be mapped to actual payer names

