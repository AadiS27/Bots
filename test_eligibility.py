"""Test script for eligibility check with improved parsing."""

import json
from pathlib import Path

from bots import EligibilityBot
from config import settings
from core import setup_logging, set_request_id, clear_request_id
from domain import EligibilityRequest
from datetime import datetime


def parse_date(date_str: str):
    """Parse date string in ISO format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def main():
    """Run a test eligibility check."""
    setup_logging(log_level="INFO")
    
    # Load test input
    input_path = Path("sample/input_eligibility.json")
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return
    
    data = json.loads(input_path.read_text())
    
    # Build EligibilityRequest
    request = EligibilityRequest(
        request_id=data["request_id"],
        payer_name=data["payer_name"],
        member_id=data["member_id"],
        patient_last_name=data["patient_last_name"],
        patient_first_name=data.get("patient_first_name"),
        dob=parse_date(data["dob"]),
        dos_from=parse_date(data["dos_from"]),
        dos_to=parse_date(data["dos_to"]) if data.get("dos_to") else None,
        service_type_code=data.get("service_type_code"),
        provider_name=data.get("provider_name"),
        provider_npi=data.get("provider_npi"),
    )
    
    set_request_id(request.request_id)
    
    print("\n" + "="*60)
    print("ELIGIBILITY CHECK TEST")
    print("="*60)
    print(f"Request ID: {request.request_id}")
    print(f"Payer: {request.payer_name}")
    print(f"Member ID: {request.member_id}")
    print(f"Provider Name: {request.provider_name}")
    print(f"Provider NPI: {request.provider_npi}")
    print("="*60 + "\n")
    
    # Initialize bot
    bot = EligibilityBot(
        base_url=settings.BASE_URL,
        username=settings.USERNAME,
        password=settings.PASSWORD,
        headless=False,  # Show browser for debugging
        artifacts_dir=settings.ARTIFACTS_DIR,
    )
    
    try:
        # Process request
        result = bot.process_request(request)
        
        # Display results
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        print(f"Coverage Status: {result.coverage_status}")
        print(f"Plan Name: {result.plan_name}")
        print(f"Plan Type: {result.plan_type}")
        print(f"Coverage Dates: {result.coverage_start_date} to {result.coverage_end_date}")
        print(f"Deductible Individual: ${result.deductible_individual}" if result.deductible_individual else "Deductible Individual: N/A")
        print(f"Deductible Remaining: ${result.deductible_remaining_individual}" if result.deductible_remaining_individual else "Deductible Remaining: N/A")
        print(f"OOP Max Individual: ${result.oop_max_individual}" if result.oop_max_individual else "OOP Max Individual: N/A")
        print(f"OOP Max Family: ${result.oop_max_family}" if result.oop_max_family else "OOP Max Family: N/A")
        print(f"Benefit Lines: {len(result.benefit_lines)}")
        
        if result.benefit_lines:
            print("\nBenefit Lines:")
            for i, benefit in enumerate(result.benefit_lines, 1):
                print(f"  {i}. {benefit.benefit_category}")
                if benefit.copay_amount:
                    print(f"     Copay: ${benefit.copay_amount}")
                if benefit.network_tier:
                    print(f"     Network: {benefit.network_tier}")
        
        print("\n" + "="*60)
        print("TEST COMPLETED SUCCESSFULLY")
        print("="*60)
        
        # Save results
        output_path = Path("sample/output_test.json")
        output_path.write_text(result.model_dump_json(indent=2))
        print(f"\nResults saved to: {output_path}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        bot.close()
        clear_request_id()


if __name__ == "__main__":
    main()

