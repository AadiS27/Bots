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

---

## Claims Submission Endpoint

**POST** `/claims`

Submit a professional claim through the Availity portal.

### Request Headers
```
Content-Type: application/json
```

### Request Body (JSON)
```json
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

### Expected Response (Success)
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

### Expected Response (Error)
```json
{
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "FAILED",
  "claimSubmitted": null,
  "transactionId": null,
  "claimId": null,
  "patientAccountNumber": null,
  "submissionType": null,
  "submissionDate": null,
  "datesOfService": null,
  "patientName": null,
  "subscriberId": null,
  "billingProviderName": null,
  "billingProviderNpi": null,
  "billingProviderTaxId": null,
  "totalCharges": null,
  "errorMessage": "Error message here",
  "rawResponseHtmlPath": null
}
```

### cURL Command
```bash
curl --location 'http://localhost:8000/claims' \
--header 'Content-Type: application/json' \
--data '{
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
}'
```

