import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from app.database import init_db, list_invoices, get_kpis
from app.sample_generator import generate_all_samples
from app.agent.orchestrator import process_invoice_file
from app.config import SAMPLES_DIR, DB_PATH


def run_tests():
    print("==================================================")
    print("  RUNNING AUTONOMOUS INVOICE AGENT TEST SUITE     ")
    print("==================================================")

    # Initialize fresh DB
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()

    # Generate sample PDFs
    files = generate_all_samples()
    print(f"Generated {len(files)} sample PDFs.")

    # 1. Test Valid Benchmark Invoice (INV-1024)
    print("\n--- Test 1: Valid Benchmark Invoice (INV-1024) ---")
    p1 = SAMPLES_DIR / "1_valid_invoice_1024.pdf"
    rec1 = process_invoice_file(p1, p1.read_bytes())
    
    assert rec1.vendor_name == "ABC Suppliers", f"Expected ABC Suppliers, got {rec1.vendor_name}"
    assert rec1.invoice_number == "INV-1024", f"Expected INV-1024, got {rec1.invoice_number}"
    assert rec1.amount_total == 84500.0, f"Expected 84500.0, got {rec1.amount_total}"
    assert rec1.validation_status == "verified", f"Expected verified, got {rec1.validation_status}"
    assert rec1.duplicate_check == "unique", f"Expected unique, got {rec1.duplicate_check}"
    assert rec1.fraud_flag is False, "Expected fraud_flag to be False"
    assert rec1.payment_status in ("due_soon", "pending"), f"Expected due_soon/pending, got {rec1.payment_status}"
    print("  ✓ Fields extracted correctly:", rec1.vendor_name, rec1.invoice_number, rec1.amount_total)
    print("  ✓ Validation status: verified")
    print("  ✓ Duplicate check: unique")
    print("  ✓ Payment status:", rec1.payment_status, f"(days: {rec1.days_due})")

    # 2. Test Duplicate Detection (Re-upload INV-1024)
    print("\n--- Test 2: Duplicate Detection ---")
    rec2 = process_invoice_file(p1, p1.read_bytes(), source_filename="1_valid_invoice_1024_copy.pdf")
    assert rec2.duplicate_check == "duplicate", f"Expected duplicate, got {rec2.duplicate_check}"
    assert rec2.duplicate_of_id == rec1.invoice_id, f"Expected link to {rec1.invoice_id}, got {rec2.duplicate_of_id}"
    print(f"  ✓ Duplicate detected! Linked to original invoice ID: {rec2.duplicate_of_id}")

    # 3. Test Arithmetic Tax Mismatch Detection
    print("\n--- Test 3: Arithmetic Tax Mismatch ---")
    p2 = SAMPLES_DIR / "2_tax_mismatch_invoice.pdf"
    rec3 = process_invoice_file(p2, p2.read_bytes())
    assert rec3.validation_status == "mismatch", f"Expected mismatch, got {rec3.validation_status}"
    assert len(rec3.validation_errors) > 0, "Expected validation errors"
    print("  ✓ Mismatch flagged! Error description:")
    for err in rec3.validation_errors:
        print(f"    - {err}")

    # 4. Test Fraud Detection (Altered Bank Account for ABC Suppliers)
    print("\n--- Test 4: Vendor Bank Detail Fraud Risk ---")
    p3 = SAMPLES_DIR / "3_fraud_bank_mismatch.pdf"
    rec4 = process_invoice_file(p3, p3.read_bytes())
    assert rec4.fraud_flag is True, f"Expected fraud_flag=True, got {rec4.fraud_flag}"
    assert rec4.fraud_reason is not None, "Expected fraud_reason"
    print(f"  ✓ Fraud detected! Reason: {rec4.fraud_reason}")

    # 5. Test Overdue Payment Tracking
    print("\n--- Test 5: Overdue Payment Tracking ---")
    p4 = SAMPLES_DIR / "4_overdue_invoice.pdf"
    rec5 = process_invoice_file(p4, p4.read_bytes())
    assert rec5.payment_status == "overdue", f"Expected overdue, got {rec5.payment_status}"
    assert rec5.days_due < 0, f"Expected negative days_due, got {rec5.days_due}"
    print(f"  ✓ Overdue status assigned! {rec5.days_due} days ({rec5.due_date})")

    # 6. Test Incomplete Invoice (Missing Required Fields)
    print("\n--- Test 6: Incomplete Invoice Validation ---")
    p5 = SAMPLES_DIR / "5_incomplete_invoice.pdf"
    rec6 = process_invoice_file(p5, p5.read_bytes())
    assert rec6.validation_status == "incomplete", f"Expected incomplete, got {rec6.validation_status}"
    print("  ✓ Incomplete invoice flagged! Missing fields:")
    for err in rec6.validation_errors:
        print(f"    - {err}")

    # 7. Test Database KPIs
    print("\n--- Test 7: Database Aggregation & KPIs ---")
    kpis = get_kpis()
    print("  ✓ KPI stats:", kpis)
    assert kpis["total_count"] == 6
    assert kpis["duplicate_count"] >= 1
    assert kpis["fraud_count"] >= 1
    assert kpis["overdue_count"] >= 1

    print("\n==================================================")
    print("  ALL 7 AGENT TEST SUITE SUITES PASSED 100%!      ")
    print("==================================================")


if __name__ == "__main__":
    run_tests()
