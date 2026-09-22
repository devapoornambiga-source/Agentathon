import io
from pathlib import Path
from typing import List, Dict, Any
from app.config import SAMPLES_DIR


def build_pdf(lines: List[str]) -> bytes:
    """Generates a standard compliant single-page PDF with lines of text."""
    content = "BT\n/F1 11 Tf\n16 TL\n50 730 Td\n"
    for line in lines:
        if line == "---":
            content += "() '\n"
        else:
            esc = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            content += f"({esc}) '\n"
    content += "ET"
    c_bytes = content.encode("utf-8")

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = [0]

    # obj 1: Catalog
    offsets.append(buf.tell())
    buf.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

    # obj 2: Pages
    offsets.append(buf.tell())
    buf.write(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

    # obj 3: Page
    offsets.append(buf.tell())
    buf.write(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n")

    # obj 4: Font
    offsets.append(buf.tell())
    buf.write(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    # obj 5: Contents
    offsets.append(buf.tell())
    buf.write(f"5 0 obj\n<< /Length {len(c_bytes)} >>\nstream\n".encode("ascii"))
    buf.write(c_bytes)
    buf.write(b"\nendstream\nendobj\n")

    # xref
    xref_pos = buf.tell()
    buf.write(b"xref\n0 6\n")
    buf.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.write(f"{off:010d} 00000 n \n".encode("ascii"))
    buf.write(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii"))

    return buf.getvalue()


SAMPLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "1_valid_invoice_1024.pdf": {
        "title": "PRD Benchmark (INV-1024)",
        "scenario": "Verified & Due in 8 days",
        "description": "Clean invoice matching PRD Section 9 benchmark (₹84,500 due 30 Sept 2026).",
        "lines": [
            "==================================================",
            "                   TAX INVOICE                    ",
            "==================================================",
            "Vendor: ABC Suppliers",
            "Invoice Number: INV-1024",
            "Invoice Date: 2026-09-15",
            "Due Date: 2026-09-30",
            "Currency: INR",
            "---",
            "Billed To: TechCorp Solutions Pvt Ltd",
            "---",
            "Bank Details:",
            "Account Name: ABC Suppliers",
            "Account Number: 987654321012",
            "IFSC Code: HDFC0001234",
            "---",
            "Description                  Qty    Unit Price    Total",
            "Cloud-Compute-Hosting        1      50000         50000",
            "Enterprise-Support-SLA       1      25000         25000",
            "---",
            "Subtotal: 75000",
            "Tax (GST 18%): 9500",
            "Total Amount: 84500",
            "=================================================="
        ]
    },
    "2_tax_mismatch_invoice.pdf": {
        "title": "Arithmetic Tax Mismatch",
        "scenario": "Triggers 'mismatch' flag",
        "description": "Calculates Subtotal (50,000) + Tax (9,000) = 59,000, but Total states 65,000.",
        "lines": [
            "==================================================",
            "                   TAX INVOICE                    ",
            "==================================================",
            "Vendor: Apex Cloud Technologies",
            "Invoice Number: INV-2088",
            "Invoice Date: 2026-09-18",
            "Due Date: 2026-10-05",
            "Currency: INR",
            "---",
            "Bank Details:",
            "Account Name: Apex Cloud Technologies",
            "Account Number: 112233445566",
            "IFSC Code: ICIC0004567",
            "---",
            "Description                  Qty    Unit Price    Total",
            "Annual-Software-License      1      50000         50000",
            "---",
            "Subtotal: 50000",
            "Tax (GST): 9000",
            "Total Amount: 65000",
            "=================================================="
        ]
    },
    "3_fraud_bank_mismatch.pdf": {
        "title": "Vendor Bank Fraud Risk",
        "scenario": "Triggers 'fraud_flag = true'",
        "description": "ABC Suppliers with an altered bank account number (differs from original 987654321012).",
        "lines": [
            "==================================================",
            "                   TAX INVOICE                    ",
            "==================================================",
            "Vendor: ABC Suppliers",
            "Invoice Number: INV-1099",
            "Invoice Date: 2026-09-20",
            "Due Date: 2026-10-10",
            "Currency: INR",
            "---",
            "Bank Details:",
            "Account Name: ABC Suppliers",
            "Account Number: 888877776666",
            "IFSC Code: HDFC0001234",
            "---",
            "Description                  Qty    Unit Price    Total",
            "Server-Migration-Consulting  1      30000         30000",
            "---",
            "Subtotal: 30000",
            "Tax (GST): 5400",
            "Total Amount: 35400",
            "=================================================="
        ]
    },
    "4_overdue_invoice.pdf": {
        "title": "Overdue Payment Notice",
        "scenario": "Triggers 'overdue' status",
        "description": "Past due invoice with due date 05 Sept 2026 (overdue by 17 days).",
        "lines": [
            "==================================================",
            "                   TAX INVOICE                    ",
            "==================================================",
            "Vendor: Global Logistics Corp",
            "Invoice Number: INV-0942",
            "Invoice Date: 2026-08-10",
            "Due Date: 2026-09-05",
            "Currency: INR",
            "---",
            "Bank Details:",
            "Account Name: Global Logistics Corp",
            "Account Number: 554433221100",
            "IFSC Code: SBIN0009876",
            "---",
            "Description                  Qty    Unit Price    Total",
            "Freight-Forwarding-Shipment  2      20000         40000",
            "---",
            "Subtotal: 40000",
            "Tax (GST): 7200",
            "Total Amount: 47200",
            "=================================================="
        ]
    },
    "5_incomplete_invoice.pdf": {
        "title": "Missing Required Fields",
        "scenario": "Triggers 'incomplete' status",
        "description": "Invoice missing invoice number and grand total fields.",
        "lines": [
            "==================================================",
            "                     INVOICE                      ",
            "==================================================",
            "Vendor: Zenith Digital Marketing",
            "Invoice Date: 2026-09-21",
            "Currency: INR",
            "---",
            "Description                  Qty    Unit Price    Total",
            "SEO-Campaign-Adwords         1      15000         15000",
            "---",
            "Subtotal: 15000",
            "Tax: 2700",
            "=================================================="
        ]
    }
}


def generate_all_samples() -> List[str]:
    """Generates all 5 sample PDF invoices in SAMPLES_DIR."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    generated_files: List[str] = []

    for filename, item in SAMPLE_DEFINITIONS.items():
        file_path = SAMPLES_DIR / filename
        pdf_bytes = build_pdf(item["lines"])
        file_path.write_bytes(pdf_bytes)
        generated_files.append(filename)

    return generated_files
