from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class BankDetails(BaseModel):
    account_name: str = ""
    account_number: str = ""
    ifsc_or_swift: str = ""


class LineItem(BaseModel):
    description: str = ""
    quantity: float = 1.0
    unit_price: float = 0.0
    line_total: float = 0.0


class InvoiceRecord(BaseModel):
    invoice_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vendor_name: str = ""
    invoice_number: str = ""
    invoice_date: str = ""  # YYYY-MM-DD
    due_date: str = ""      # YYYY-MM-DD
    amount_subtotal: float = 0.0
    tax_amount: float = 0.0
    amount_total: float = 0.0
    currency: str = "INR"
    bank_details: BankDetails = Field(default_factory=BankDetails)
    line_items: List[LineItem] = Field(default_factory=list)
    validation_status: str = "incomplete"  # verified | incomplete | mismatch
    validation_errors: List[str] = Field(default_factory=list)
    duplicate_check: str = "unique"        # unique | duplicate
    duplicate_of_id: Optional[str] = None
    fraud_flag: bool = False
    fraud_reason: Optional[str] = None
    payment_status: str = "pending"        # pending | due_soon | overdue | paid
    days_due: int = 0
    source_file: str = ""
    file_hash: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    summary_text: str = ""


class ExtractionResult(BaseModel):
    vendor_name: str = ""
    invoice_number: str = ""
    invoice_date: str = ""
    due_date: str = ""
    amount_subtotal: float = 0.0
    tax_amount: float = 0.0
    amount_total: float = 0.0
    currency: str = "INR"
    bank_details: BankDetails = Field(default_factory=BankDetails)
    line_items: List[LineItem] = Field(default_factory=list)
    raw_text: str = ""
    file_hash: str = ""
