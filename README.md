# Availity Bots API

Automated Availity portal operations API for Claims Submission, Claim Status Check, and Eligibility Verification.

## Features

- **Claim Status Check**: Check the status of submitted claims
- **Claims Submission**: Submit professional claims to insurance payers
- **Eligibility Verification**: Verify patient eligibility and coverage
- **Shared WebDriver**: Efficient browser instance management with thread-safe access
- **RESTful API**: FastAPI-based endpoints for easy integration

## Prerequisites

- Python 3.11 or higher
- Chrome browser installed
- ChromeDriver (automatically managed by the project)

## Installation

1. **Clone the repository** (if not already done):
```bash
   git clone <repository-url>
   cd Bots
   ```

2. **Install dependencies**:
```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials**:
   
   Create a `.env` file in the project root or set environment variables:
   ```env
   BASE_URL=https://apps.availity.com
   USERNAME=your_username
   PASSWORD=your_password
   ARTIFACTS_DIR=artifacts
   ```
   
   Or edit `config/settings.py` directly with your credentials.

## Running the API Server

### Option 1: Using run_api.py (Recommended)
```bash
python run_api.py
```

### Option 2: Using api/run_server.py
```bash
python api/run_server.py
```

### Option 3: Using uvicorn directly
```bash
uvicorn api.server:app --host 127.0.0.1 --port 8000
```

The server will start on `http://127.0.0.1:8000`

## API Endpoints

### Health Check
```bash
GET http://localhost:8000/health
```

### Claim Status Check
```bash
POST http://localhost:8000/claim-status
Content-Type: application/json

{
  "request_id": 201,
  "payer_name": "AETNA (COMMERCIAL & MEDICARE)",
  "payer_claim_id": null,
  "provider_claim_id": "818743774",
  "member_id": "W232596158",
  "patient_last_name": "URBAN",
  "patient_first_name": "IRELIN",
  "patient_dob": "2004-09-21",
  "subscriber_last_name": "URBAN",
  "subscriber_first_name": "IRELIN",
  "subscriber_same_as_patient": true,
  "provider_npi": "1346236833",
  "dos_from": "2025-06-27",
  "dos_to": "2025-06-27",
  "claim_amount": null
}
```

### Claims Submission
```bash
POST http://localhost:8000/claims
Content-Type: application/json

{
  "tradingPartnerServiceId": null,
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
      "placeOfServiceCode": "11",
      "procedureCode": "99213",
      "diagnosisCodePointer1": "1",
      "amount": "150.00",
      "quantity": "1",
      "quantityTypeCode": "UN - Unit"
    }
  ],
  "patientPaidAmount": "100.00",
  "claimControlNumber": "CN123456",
  "diagnosisCode": "A000"
}
```

### Eligibility Check
```bash
POST http://localhost:8000/eligibility
Content-Type: application/json

{
  "payer": "AETNA (COMMERCIAL & MEDICARE)",
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
  "serviceTypeCode": "30"
}
```

## Testing the API

### Using cURL

**Claim Status:**
```bash
curl --location 'http://localhost:8000/claim-status' \
--header 'Content-Type: application/json' \
--data '{
  "request_id": 201,
  "payer_name": "AETNA (COMMERCIAL & MEDICARE)",
  "provider_claim_id": "818743774",
  "member_id": "W232596158",
  "patient_last_name": "URBAN",
  "patient_first_name": "IRELIN",
  "patient_dob": "2004-09-21",
  "subscriber_last_name": "URBAN",
  "subscriber_first_name": "IRELIN",
  "subscriber_same_as_patient": true,
  "provider_npi": "1346236833",
  "dos_from": "2025-06-27",
  "dos_to": "2025-06-27"
}'
```

### Using Python

```python
import requests

url = "http://localhost:8000/claim-status"
payload = {
    "request_id": 201,
    "payer_name": "AETNA (COMMERCIAL & MEDICARE)",
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
    "dos_to": "2025-06-27"
}

response = requests.post(url, json=payload)
print(response.json())
```

### Using Postman

See `api/POSTMAN_EXAMPLES.md` for detailed Postman collection examples.

## Project Structure

```
Bots/
├── api/                    # API server code
│   ├── server.py          # FastAPI application
│   ├── models.py          # API request/response models
│   ├── driver_manager.py  # Shared WebDriver manager
│   └── POSTMAN_EXAMPLES.md # Postman examples
├── bots/                  # Bot implementations
│   ├── claim_status_bot.py
│   ├── claims_bot.py
│   └── eligibility_bot.py
├── pages/                 # Page Object Models
├── domain/                # Domain models
├── core/                  # Core utilities
├── config.py             # Configuration
├── run_api.py            # Server startup script
└── requirements.txt      # Python dependencies
```

## Configuration

Edit `config/settings.py` or set environment variables:

- `BASE_URL`: Availity portal base URL
- `USERNAME`: Your Availity username
- `PASSWORD`: Your Availity password
- `ARTIFACTS_DIR`: Directory for saving screenshots and HTML responses

## Features

### Shared WebDriver
- Single browser instance shared across all API requests
- Thread-safe access with automatic locking
- Automatic session management and cookie persistence
- Efficient resource usage

### Error Handling
- Automatic retry for transient errors
- Detailed error messages and logging
- Artifact saving (screenshots, HTML) on errors

### Session Management
- Automatic cookie saving and loading
- Session validation
- Automatic re-login when session expires

## Response Formats

### Claim Status Response
```json
{
  "request_id": 201,
  "transaction_id": null,
  "high_level_status": "PAID",
  "status_code": null,
  "finalized_date": "2025-06-30",
  "service_dates": "06/27/2025 - 06/27/2025",
  "claim_number": "EPFDPGKP400",
  "member_name": "URBAN, IRELIN",
  "member_id": "W232596158",
  "billed_amount": 158.0,
  "paid_amount": 63.3,
  "check_or_eft_number": null,
  "payment_date": null,
  "reason_codes": []
}
```

### Claims Submission Response
```json
{
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "SUBMITTED",
  "claimSubmitted": "Claim Submitted",
  "transactionId": "123456789",
  "claimId": "EPFDPGKP400",
  "patientAccountNumber": "ACC123456",
  "submissionType": "Professional Claim",
  "submissionDate": "2025-11-20",
  "datesOfService": "11/10/2025 - 11/10/2025",
  "patientName": "SMITH, JOHN",
  "subscriberId": "123456789",
  "billingProviderName": "Provider, Medical",
  "billingProviderNpi": "1346236833",
  "billingProviderTaxId": "123456789",
  "totalCharges": "$150.00",
  "errorMessage": null,
  "rawResponseHtmlPath": null
}
```

## Troubleshooting

### WebDriver Issues
- Ensure Chrome browser is installed
- ChromeDriver is automatically downloaded by webdriver-manager
- If issues persist, check Chrome version compatibility

### Login Issues
- Verify credentials in `config/settings.py` or `.env`
- Check if Availity portal is accessible
- Review logs for specific error messages

### Port Already in Use
If port 8000 is already in use:
```bash
# Change port in run_api.py or use:
uvicorn api.server:app --host 127.0.0.1 --port 8001
```

## Development

### Running Tests
```bash
# Test claim status API
python test_claim_status_api.py
```

### Debugging
- Set `headless=False` in `api/server.py` to see browser actions (already set by default)
- Check `artifacts/` directory for screenshots and HTML responses
- Review logs for detailed execution information
- The shared WebDriver stays active between requests for faster processing

## License

[Add your license here]

## Support

For issues or questions, please [create an issue](link-to-issues) or contact the development team.
