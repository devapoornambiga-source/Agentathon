from typing import Tuple, Optional
from app.models import ExtractionResult
from app.database import (
    find_existing_by_hash,
    find_existing_by_composite,
    get_vendor_historical_bank_details
)


def check_duplicates_and_fraud(data: ExtractionResult) -> Tuple[str, Optional[str], bool, Optional[str]]:
    """
    Performs duplicate detection via hash and composite key,
    and fraud detection via vendor bank detail discrepancy check.
    
    Returns:
        (duplicate_check, duplicate_of_id, fraud_flag, fraud_reason)
    """
    duplicate_check = "unique"
    duplicate_of_id: Optional[str] = None
    fraud_flag = False
    fraud_reason: Optional[str] = None

    # 1. Exact file hash duplicate check
    if data.file_hash:
        existing_by_hash = find_existing_by_hash(data.file_hash)
        if existing_by_hash:
            duplicate_check = "duplicate"
            duplicate_of_id = existing_by_hash.invoice_id

    # 2. Composite key check (vendor + invoice number + amount)
    if duplicate_check == "unique" and data.vendor_name and data.invoice_number:
        existing_by_composite = find_existing_by_composite(
            data.vendor_name,
            data.invoice_number,
            data.amount_total
        )
        if existing_by_composite:
            duplicate_check = "duplicate"
            duplicate_of_id = existing_by_composite.invoice_id

    # 3. Fraud / Bank Details Discrepancy Check (PRD Section 8 #6)
    if data.vendor_name and (data.bank_details.account_number or data.bank_details.ifsc_or_swift):
        historical_bank = get_vendor_historical_bank_details(data.vendor_name)
        if historical_bank:
            # Check for changed account number
            if (
                data.bank_details.account_number and
                historical_bank.account_number and
                data.bank_details.account_number.strip().lower() != historical_bank.account_number.strip().lower()
            ):
                fraud_flag = True
                fraud_reason = (
                    f"Suspicious Bank Detail Change: Account number '{data.bank_details.account_number}' "
                    f"differs from established account '{historical_bank.account_number}' "
                    f"for vendor '{data.vendor_name}'."
                )
            # Check for changed IFSC/SWIFT code
            elif (
                data.bank_details.ifsc_or_swift and
                historical_bank.ifsc_or_swift and
                data.bank_details.ifsc_or_swift.strip().upper() != historical_bank.ifsc_or_swift.strip().upper()
            ):
                fraud_flag = True
                fraud_reason = (
                    f"Suspicious Bank Detail Change: IFSC/SWIFT code '{data.bank_details.ifsc_or_swift}' "
                    f"differs from established code '{historical_bank.ifsc_or_swift}' "
                    f"for vendor '{data.vendor_name}'."
                )

    return duplicate_check, duplicate_of_id, fraud_flag, fraud_reason
