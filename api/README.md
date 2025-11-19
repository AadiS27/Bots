# Availity Bots API

REST API server for automated Availity portal operations.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python api/run_server.py
```

Or using uvicorn directly:
```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- `http://localhost:8000` (recommended)
- `http://127.0.0.1:8000`

**Note:** If the server is configured to listen on `0.0.0.0`, you must still access it via `localhost:8000` or `127.0.0.1:8000` in your browser. Browsers cannot connect directly to `0.0.0.0`.

## API Endpoints

### 1. Claim Status Check
**POST** `/claim-status`

Check the status of a submitted claim.

**Example Request:**
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

### 2. Claims Submission
**POST** `/claims`

Submit a new claim.

**Example Request:**
```bash
curl --request POST \
  --url "http://localhost:8000/claims" \
  --header "Authorization: YOUR_TOKEN" \
  --header "Content-Type: application/json" \
  --data '{
    "transactionType": "Professional Claim",
    "payer": "AETNA (COMMERCIAL & MEDICARE)",
    "responsibilitySequence": "Primary",
    "subscriber": {
      "dateOfBirth": "19900115",
      "firstName": "John",
      "lastName": "Smith",
      "memberId": "123456789"
    },
    "providers": [
      {
        "npi": "1346236833",
        "organizationName": "Provider, Medical",
        "providerType": "BillingProvider"
      }
    ],
    "encounter": {
      "beginningDateOfService": "20251110",
      "endDateOfService": "20251110"
    },
    "serviceLines": [
      {
        "fromDate": "2025-11-10",
        "procedureCode": "99213",
        "amount": "150.00"
      }
    ],
    "diagnosisCode": "A000"
  }'
```

### 3. Eligibility Check
**POST** `/eligibility`

Check patient eligibility.

**Example Request:**
```bash
curl --request POST \
  --url "http://localhost:8000/eligibility" \
  --header "Authorization: YOUR_TOKEN" \
  --header "Content-Type: application/json" \
  --data '{
    "payer": "MEDICAID PENNSYLVANIA",
    "subscriber": {
      "dateOfBirth": "20140717",
      "firstName": "LOGAN",
      "lastName": "DEMERITT",
      "memberId": "2203839069"
    },
    "encounter": {
      "beginningDateOfService": "20251029"
    },
    "serviceTypeCode": "30",
    "providers": [
      {
        "npi": "1346236833",
        "organizationName": "Taylor Mc Breen",
        "providerType": "BillingProvider"
      }
    ]
  }'
```

### 4. Health Check
**GET** `/health`

Check API health status.

### 5. API Info
**GET** `/`

Get API information and available endpoints.

## Date Format

- **Input**: Dates should be in `YYYYMMDD` format (e.g., `20250627`)
- **Output**: Dates are returned in `YYYY-MM-DD` format (e.g., `2025-06-27`)

## Response Format

All endpoints return JSON responses with:
- `requestId`: Unique request identifier
- `status`: Status of the operation (SUCCESS, FAILED, PROCESSING, SUBMITTED)
- Bot-specific fields based on the endpoint
- `errorMessage`: Error details if operation failed
- `rawResponseHtmlPath`: Path to saved HTML response (if available)

## Error Handling

The API handles errors gracefully:
- Validation errors return 422 status
- Portal errors are included in the response with `status: FAILED`
- All errors include descriptive messages

## Authentication

Currently, the API accepts an optional `Authorization` header but doesn't validate it. 
You can add authentication middleware as needed.

## Notes

- The API processes requests synchronously (each request waits for completion)
- For high-volume processing, consider implementing a queue system
- Browser automation runs in headless mode by default (configurable via settings)
- All responses are saved to the artifacts directory

