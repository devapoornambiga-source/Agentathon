import sqlite3
import json
from typing import List, Optional, Dict, Any
from app.config import DB_PATH
from app.models import InvoiceRecord, BankDetails, LineItem


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id TEXT PRIMARY KEY,
                vendor_name TEXT,
                invoice_number TEXT,
                invoice_date TEXT,
                due_date TEXT,
                amount_subtotal REAL,
                tax_amount REAL,
                amount_total REAL,
                currency TEXT,
                bank_details TEXT,
                line_items TEXT,
                validation_status TEXT,
                validation_errors TEXT,
                duplicate_check TEXT,
                duplicate_of_id TEXT,
                fraud_flag INTEGER,
                fraud_reason TEXT,
                payment_status TEXT,
                days_due INTEGER,
                source_file TEXT,
                file_hash TEXT,
                created_at TEXT,
                summary_text TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vendor ON invoices(vendor_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_invoice_num ON invoices(invoice_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON invoices(file_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_status ON invoices(payment_status)")
        conn.commit()


def save_invoice(record: InvoiceRecord) -> None:
    with get_db_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO invoices (
                invoice_id, vendor_name, invoice_number, invoice_date, due_date,
                amount_subtotal, tax_amount, amount_total, currency,
                bank_details, line_items, validation_status, validation_errors,
                duplicate_check, duplicate_of_id, fraud_flag, fraud_reason,
                payment_status, days_due, source_file, file_hash, created_at, summary_text
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
        """, (
            record.invoice_id,
            record.vendor_name,
            record.invoice_number,
            record.invoice_date,
            record.due_date,
            record.amount_subtotal,
            record.tax_amount,
            record.amount_total,
            record.currency,
            record.bank_details.model_dump_json(),
            json.dumps([li.model_dump() for li in record.line_items]),
            record.validation_status,
            json.dumps(record.validation_errors),
            record.duplicate_check,
            record.duplicate_of_id,
            1 if record.fraud_flag else 0,
            record.fraud_reason,
            record.payment_status,
            record.days_due,
            record.source_file,
            record.file_hash,
            record.created_at,
            record.summary_text
        ))
        conn.commit()


def _row_to_record(row: sqlite3.Row) -> InvoiceRecord:
    bank_data = json.loads(row["bank_details"]) if row["bank_details"] else {}
    items_data = json.loads(row["line_items"]) if row["line_items"] else []
    errors_data = json.loads(row["validation_errors"]) if row["validation_errors"] else []
    
    return InvoiceRecord(
        invoice_id=row["invoice_id"],
        vendor_name=row["vendor_name"] or "",
        invoice_number=row["invoice_number"] or "",
        invoice_date=row["invoice_date"] or "",
        due_date=row["due_date"] or "",
        amount_subtotal=row["amount_subtotal"] or 0.0,
        tax_amount=row["tax_amount"] or 0.0,
        amount_total=row["amount_total"] or 0.0,
        currency=row["currency"] or "INR",
        bank_details=BankDetails(**bank_data),
        line_items=[LineItem(**item) for item in items_data],
        validation_status=row["validation_status"] or "incomplete",
        validation_errors=errors_data,
        duplicate_check=row["duplicate_check"] or "unique",
        duplicate_of_id=row["duplicate_of_id"],
        fraud_flag=bool(row["fraud_flag"]),
        fraud_reason=row["fraud_reason"],
        payment_status=row["payment_status"] or "pending",
        days_due=row["days_due"] or 0,
        source_file=row["source_file"] or "",
        file_hash=row["file_hash"] or "",
        created_at=row["created_at"] or "",
        summary_text=row["summary_text"] or ""
    )


def get_invoice(invoice_id: str) -> Optional[InvoiceRecord]:
    with get_db_connection() as conn:
        cur = conn.execute("SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,))
        row = cur.fetchone()
        if row:
            return _row_to_record(row)
    return None


def list_invoices(status_filter: Optional[str] = None, search: Optional[str] = None) -> List[InvoiceRecord]:
    with get_db_connection() as conn:
        query = "SELECT * FROM invoices WHERE 1=1"
        params: List[Any] = []

        if status_filter:
            status_filter = status_filter.lower().strip()
            if status_filter == "duplicate":
                query += " AND duplicate_check = 'duplicate'"
            elif status_filter == "fraud":
                query += " AND fraud_flag = 1"
            elif status_filter in ("verified", "incomplete", "mismatch"):
                query += " AND validation_status = ?"
                params.append(status_filter)
            elif status_filter in ("pending", "due_soon", "overdue", "paid"):
                query += " AND payment_status = ?"
                params.append(status_filter)

        if search:
            query += " AND (vendor_name LIKE ? OR invoice_number LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        query += " ORDER BY created_at DESC"
        cur = conn.execute(query, params)
        return [_row_to_record(r) for r in cur.fetchall()]


def find_existing_by_hash(file_hash: str) -> Optional[InvoiceRecord]:
    if not file_hash:
        return None
    with get_db_connection() as conn:
        cur = conn.execute("SELECT * FROM invoices WHERE file_hash = ? ORDER BY created_at ASC LIMIT 1", (file_hash,))
        row = cur.fetchone()
        if row:
            return _row_to_record(row)
    return None


def find_existing_by_composite(vendor_name: str, invoice_number: str, amount_total: float) -> Optional[InvoiceRecord]:
    if not vendor_name or not invoice_number:
        return None
    with get_db_connection() as conn:
        cur = conn.execute("""
            SELECT * FROM invoices 
            WHERE LOWER(TRIM(vendor_name)) = LOWER(TRIM(?))
              AND LOWER(TRIM(invoice_number)) = LOWER(TRIM(?))
              AND ABS(amount_total - ?) < 0.01
            ORDER BY created_at ASC LIMIT 1
        """, (vendor_name, invoice_number, amount_total))
        row = cur.fetchone()
        if row:
            return _row_to_record(row)
    return None


def get_vendor_historical_bank_details(vendor_name: str) -> Optional[BankDetails]:
    if not vendor_name:
        return None
    with get_db_connection() as conn:
        cur = conn.execute("""
            SELECT bank_details FROM invoices 
            WHERE LOWER(TRIM(vendor_name)) = LOWER(TRIM(?))
              AND validation_status = 'verified'
              AND fraud_flag = 0
            ORDER BY created_at ASC LIMIT 1
        """, (vendor_name,))
        row = cur.fetchone()
        if row and row["bank_details"]:
            data = json.loads(row["bank_details"])
            if data.get("account_number"):
                return BankDetails(**data)
    return None


def update_payment_status(invoice_id: str, new_status: str) -> bool:
    with get_db_connection() as conn:
        cur = conn.execute("UPDATE invoices SET payment_status = ? WHERE invoice_id = ?", (new_status, invoice_id))
        conn.commit()
        return cur.rowcount > 0


def delete_invoice(invoice_id: str) -> bool:
    with get_db_connection() as conn:
        cur = conn.execute("DELETE FROM invoices WHERE invoice_id = ?", (invoice_id,))
        conn.commit()
        return cur.rowcount > 0


def get_kpis() -> Dict[str, Any]:
    with get_db_connection() as conn:
        cur = conn.execute("""
            SELECT 
                COUNT(*) as total_count,
                COALESCE(SUM(amount_total), 0) as total_amount,
                SUM(CASE WHEN validation_status = 'verified' THEN 1 ELSE 0 END) as verified_count,
                SUM(CASE WHEN duplicate_check = 'duplicate' THEN 1 ELSE 0 END) as duplicate_count,
                SUM(CASE WHEN fraud_flag = 1 THEN 1 ELSE 0 END) as fraud_count,
                SUM(CASE WHEN payment_status = 'overdue' THEN 1 ELSE 0 END) as overdue_count,
                SUM(CASE WHEN payment_status = 'due_soon' THEN 1 ELSE 0 END) as due_soon_count,
                SUM(CASE WHEN payment_status = 'paid' THEN 1 ELSE 0 END) as paid_count
            FROM invoices
        """)
        row = cur.fetchone()
        return {
            "total_count": row["total_count"] or 0,
            "total_amount": round(row["total_amount"] or 0.0, 2),
            "verified_count": row["verified_count"] or 0,
            "duplicate_count": row["duplicate_count"] or 0,
            "fraud_count": row["fraud_count"] or 0,
            "overdue_count": row["overdue_count"] or 0,
            "due_soon_count": row["due_soon_count"] or 0,
            "paid_count": row["paid_count"] or 0
        }
