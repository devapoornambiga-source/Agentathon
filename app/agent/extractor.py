import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pypdf import PdfReader
from app.models import ExtractionResult, BankDetails, LineItem


def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def normalize_date(date_str: str) -> str:
    """Standardize date strings into YYYY-MM-DD format."""
    if not date_str:
        return ""
    date_str = date_str.strip()
    
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d.%m.%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d-%b-%Y",
        "%d-%B-%Y"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Fallback heuristic for strings like "30 Sept 2026" or "30th Sep 2026"
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
    cleaned = re.sub(r'Sept', 'Sep', cleaned, flags=re.IGNORECASE)
    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return date_str


def parse_number(val_str: str) -> float:
    if not val_str:
        return 0.0
    cleaned = re.sub(r'[^\d.]', '', val_str)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text
    except Exception as e:
        return f"[PDF Extraction Error: {e}]"


def extract_fields_from_text(raw_text: str, file_hash: str) -> ExtractionResult:
    """Intelligent heuristic and layout extraction matching PRD fields."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    
    vendor_name = ""
    invoice_number = ""
    invoice_date = ""
    due_date = ""
    amount_subtotal = 0.0
    tax_amount = 0.0
    amount_total = 0.0
    currency = "INR"
    
    bank_account_name = ""
    bank_account_number = ""
    bank_ifsc_swift = ""
    
    line_items: List[LineItem] = []

    # Currency detection
    if "$" in raw_text or "USD" in raw_text:
        currency = "USD"
    elif "€" in raw_text or "EUR" in raw_text:
        currency = "EUR"
    elif "£" in raw_text or "GBP" in raw_text:
        currency = "GBP"
    else:
        currency = "INR"

    # 1. Vendor Name
    vendor_match = re.search(r'(?:Vendor|Supplier|From|Billed\s*By|Company)\s*[:=\-]\s*([^\n\r,]+)', raw_text, re.IGNORECASE)
    if vendor_match:
        vendor_name = vendor_match.group(1).strip()
    else:
        # If no explicit label, look at top lines that look like a business name
        for line in lines[:4]:
            if not re.search(r'===|---|invoice|tax|bill|date|number|gst', line, re.IGNORECASE) and len(line) > 3:
                vendor_name = line
                break

    # 2. Invoice Number (Requires explicit prefix like Invoice Number:, Invoice #, INV No, etc.)
    inv_num_match = re.search(
        r'(?:Invoice\s*(?:Number|No\.?|#)|(?:\bINV|\bBill)\s*(?:Number|No\.?|#))\s*[:#\-]?\s*([A-Z0-9\-_/]+)',
        raw_text,
        re.IGNORECASE
    )
    if inv_num_match:
        invoice_number = inv_num_match.group(1).strip()
    else:
        # Fallback to standalone "INV-XXXX" pattern
        standalone_inv = re.search(r'\b(INV-[0-9A-Z]+)\b', raw_text, re.IGNORECASE)
        if standalone_inv:
            invoice_number = standalone_inv.group(1).strip()

    # 3. Invoice Date
    date_match = re.search(
        r'(?:Invoice\s*Date|Issue\s*Date|Date\s*of\s*Invoice|\bDate)\s*[:=\-]\s*([0-9]{1,4}[-/.][0-9]{1,2}[-/.][0-9]{1,4}|[0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})',
        raw_text,
        re.IGNORECASE
    )
    if date_match:
        invoice_date = normalize_date(date_match.group(1).strip())

    # 4. Due Date
    due_match = re.search(
        r'(?:Due\s*Date|Payment\s*Due|\bDue)\s*[:=\-]\s*([0-9]{1,4}[-/.][0-9]{1,2}[-/.][0-9]{1,4}|[0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})',
        raw_text,
        re.IGNORECASE
    )
    if due_match:
        due_date = normalize_date(due_match.group(1).strip())

    # 5. Bank Details
    acct_num_match = re.search(
        r'(?:Account\s*(?:Number|No\.?)|A/C\s*(?:No\.?|Number)|Bank\s*A/C)\s*[:=\-]\s*([0-9A-Z]{6,24})',
        raw_text,
        re.IGNORECASE
    )
    if acct_num_match:
        bank_account_number = acct_num_match.group(1).strip()

    ifsc_match = re.search(
        r'(?:IFSC|SWIFT|BIC)(?:\s*(?:Code|No\.?))?\s*[:=\-]\s*([A-Z0-9]{8,11})',
        raw_text,
        re.IGNORECASE
    )
    if ifsc_match:
        bank_ifsc_swift = ifsc_match.group(1).strip()

    acct_name_match = re.search(
        r'(?:Account\s*Name|Beneficiary(?:\s*Name)?|A/C\s*Name)\s*[:=\-]\s*([^\n\r,]+)',
        raw_text,
        re.IGNORECASE
    )
    if acct_name_match:
        bank_account_name = acct_name_match.group(1).strip()
    elif vendor_name:
        bank_account_name = vendor_name

    # 6. Amounts (Subtotal, Tax, Total)
    subtotal_match = re.search(
        r'(?:Subtotal|Sub-Total|Net\s*Amount)\s*[:=\-]\s*(?:₹|\$|€|INR|USD)?\s*([0-9,]+\.?[0-9]*)',
        raw_text,
        re.IGNORECASE
    )
    if subtotal_match:
        amount_subtotal = parse_number(subtotal_match.group(1))

    tax_match = re.search(
        r'(?:Tax(?:\s*Amount)?|GST|VAT|CGST\s*\+\s*SGST|IGST)(?:\s*\([^)]*\))?\s*[:=\-]\s*(?:₹|\$|€|INR|USD)?\s*([0-9,]+\.?[0-9]*)',
        raw_text,
        re.IGNORECASE
    )
    if tax_match:
        tax_amount = parse_number(tax_match.group(1))

    total_match = re.search(
        r'(?:Grand\s*Total|Total\s*Amount|Amount\s*Total|Invoice\s*Total|\bTotal)\s*[:=\-]\s*(?:₹|\$|€|INR|USD)?\s*([0-9,]+\.?[0-9]*)',
        raw_text,
        re.IGNORECASE
    )
    if total_match:
        amount_total = parse_number(total_match.group(1))

    # 7. Line Items (table row parsing)
    # Looking for lines with format: <description> <qty> <price> <total>
    for line in lines:
        row_match = re.search(r'^([A-Za-z0-9\s\-_/&]+?)\s+(\d+(?:\.\d+)?)\s+(?:₹|\$|€)?\s*([\d,]+\.?\d*)\s+(?:₹|\$|€)?\s*([\d,]+\.?\d*)$', line)
        if row_match:
            desc = row_match.group(1).strip()
            # Avoid header or separator rows
            if not re.search(r'description|item|quantity|qty|price|amount|total|===|---', desc, re.IGNORECASE):
                qty = parse_number(row_match.group(2))
                unit_p = parse_number(row_match.group(3))
                ltotal = parse_number(row_match.group(4))
                line_items.append(LineItem(
                    description=desc,
                    quantity=qty,
                    unit_price=unit_p,
                    line_total=ltotal
                ))

    # If subtotal wasn't explicitly stated but line items exist
    if amount_subtotal == 0.0 and line_items:
        amount_subtotal = round(sum(li.line_total for li in line_items), 2)

    # If total wasn't explicitly stated but subtotal and tax exist
    if amount_total == 0.0 and (amount_subtotal > 0 or tax_amount > 0):
        amount_total = round(amount_subtotal + tax_amount, 2)

    return ExtractionResult(
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        due_date=due_date,
        amount_subtotal=amount_subtotal,
        tax_amount=tax_amount,
        amount_total=amount_total,
        currency=currency,
        bank_details=BankDetails(
            account_name=bank_account_name,
            account_number=bank_account_number,
            ifsc_or_swift=bank_ifsc_swift
        ),
        line_items=line_items,
        raw_text=raw_text,
        file_hash=file_hash
    )


def extract_invoice_data(file_path: Path, file_bytes: bytes) -> ExtractionResult:
    """Primary entrypoint for document understanding layer."""
    file_hash = compute_file_hash(file_bytes)
    extension = file_path.suffix.lower()

    if extension == ".pdf":
        raw_text = extract_text_from_pdf(file_path)
    else:
        try:
            raw_text = file_bytes.decode('utf-8', errors='ignore')
        except Exception:
            raw_text = ""

    result = extract_fields_from_text(raw_text, file_hash)
    return result
