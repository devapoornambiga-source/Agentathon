from datetime import datetime, date
from typing import Tuple
from app.models import ExtractionResult


def calculate_due_status(due_date_str: str) -> Tuple[str, int, str]:
    """
    Calculates payment status, days remaining/overdue, and display string.
    Returns: (payment_status, days_due, payment_desc)
    payment_status: 'pending' | 'due_soon' | 'overdue' | 'paid'
    """
    if not due_date_str:
        return "pending", 0, "No due date specified"

    try:
        due_dt = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except ValueError:
        return "pending", 0, "Invalid due date format"

    today = date.today()
    delta_days = (due_dt - today).days

    if delta_days < 0:
        overdue_days = abs(delta_days)
        return "overdue", delta_days, f"Overdue by {overdue_days} day{'s' if overdue_days != 1 else ''}"
    elif delta_days == 0:
        return "due_soon", 0, "Due today"
    elif delta_days <= 7:
        return "due_soon", delta_days, f"Due in {delta_days} day{'s' if delta_days != 1 else ''}"
    else:
        return "pending", delta_days, f"Due in {delta_days} days"


def generate_summary_text(
    data: ExtractionResult,
    validation_status: str,
    duplicate_check: str,
    payment_desc: str
) -> str:
    """
    Formats clean readable summary matching PRD Section 9:
    Vendor: ABC Suppliers
    Invoice: INV-1024
    Amount: ₹84,500
    Due: 30 Sept 2026
    Status: Verified
    Duplicate: No
    Payment: Due in 9 days
    """
    curr_symbol = "₹" if data.currency == "INR" else ("$" if data.currency == "USD" else data.currency + " ")
    
    # Format due date nicely if available (e.g. 30 Sep 2026)
    due_display = data.due_date
    if data.due_date:
        try:
            dt = datetime.strptime(data.due_date, "%Y-%m-%d")
            due_display = dt.strftime("%d %b %Y")
        except ValueError:
            pass

    status_display = validation_status.capitalize()
    duplicate_display = "Yes (Duplicate)" if duplicate_check == "duplicate" else "No"
    
    amount_str = f"{curr_symbol}{data.amount_total:,.2f}".replace(".00", "")

    summary_lines = [
        f"Vendor: {data.vendor_name or 'N/A'}",
        f"Invoice: {data.invoice_number or 'N/A'}",
        f"Amount: {amount_str}",
        f"Due: {due_display or 'N/A'}",
        f"Status: {status_display}",
        f"Duplicate: {duplicate_display}",
        f"Payment: {payment_desc}"
    ]
    return "\n".join(summary_lines)
