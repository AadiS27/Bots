# Postman API Examples

## Claim Status Check

### Request Details
- **Method:** POST
- **URL:** `http://localhost:8000/claim-status`
- **Headers:**
  - `Content-Type: application/json`
  - `Authorization: YOUR_TOKEN` (optional)

### Request Body (JSON)
```json
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

### Expected Response (Success)
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

### Expected Response (Error)
```json
{
  "request_id": 201,
  "transaction_id": null,
  "high_level_status": null,
  "status_code": null,
  "finalized_date": null,
  "service_dates": null,
  "claim_number": null,
  "member_name": null,
  "member_id": null,
  "billed_amount": null,
  "paid_amount": null,
  "check_or_eft_number": null,
  "payment_date": null,
  "reason_codes": []
}
```

## cURL Command
```bash
curl --location 'http://localhost:8000/claim-status' \
--header 'Content-Type: application/json' \
--data '{
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
}'
```

