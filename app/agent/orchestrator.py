from pathlib import Path
from typing import Optional
from app.models import InvoiceRecord
from app.agent.extractor import extract_invoice_data
from app.agent.validator import validate_invoice
from app.agent.fraud_detector import check_duplicates_and_fraud
from app.agent.payment_tracker import calculate_due_status, generate_summary_text
from app.database import save_invoice


def process_invoice_file(file_path: Path, file_bytes: bytes, source_filename: Optional[str] = None) -> InvoiceRecord:
    """
    Autonomous Invoice Processing Agent Orchestrator:
    1. Ingestion: Ingests PDF/image file.
    2. Document Understanding & Extraction: Extracts fields into structured schema.
    3. Validation Engine: Verifies required fields and arithmetic calculations.
    4. Duplicate & Fraud Detector: Flags duplicate submissions and vendor bank discrepancies.
    5. Payment Tracker: Calculates due status and days remaining.
    6. Summary Formatter: Generates concise PRD Section 9 summary.
    7. Storage: Persists structured record in SQLite.
    """
    filename = source_filename or file_path.name

    # Step 1 & 2: Extraction
    extracted = extract_invoice_data(file_path, file_bytes)

    # Step 3: Validation
    validation_status, validation_errors = validate_invoice(extracted)

    # Step 4: Duplicate and Fraud Check
    duplicate_check, duplicate_of_id, fraud_flag, fraud_reason = check_duplicates_and_fraud(extracted)

    # Step 5: Payment Due Tracking
    payment_status, days_due, payment_desc = calculate_due_status(extracted.due_date)

    # Step 6: Summary Generation (PRD Section 9 format)
    summary_text = generate_summary_text(
        extracted,
        validation_status,
        duplicate_check,
        payment_desc
    )

    # Step 7: Build persistent InvoiceRecord
    record = InvoiceRecord(
        vendor_name=extracted.vendor_name,
        invoice_number=extracted.invoice_number,
        invoice_date=extracted.invoice_date,
        due_date=extracted.due_date,
        amount_subtotal=extracted.amount_subtotal,
        tax_amount=extracted.tax_amount,
        amount_total=extracted.amount_total,
        currency=extracted.currency,
        bank_details=extracted.bank_details,
        line_items=extracted.line_items,
        validation_status=validation_status,
        validation_errors=validation_errors,
        duplicate_check=duplicate_check,
        duplicate_of_id=duplicate_of_id,
        fraud_flag=fraud_flag,
        fraud_reason=fraud_reason,
        payment_status=payment_status,
        days_due=days_due,
        source_file=filename,
        file_hash=extracted.file_hash,
        summary_text=summary_text
    )

    # Step 8: Persist to DB
    save_invoice(record)

    return record
