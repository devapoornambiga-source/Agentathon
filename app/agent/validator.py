from typing import Tuple, List
from app.models import ExtractionResult


def validate_invoice(data: ExtractionResult) -> Tuple[str, List[str]]:
    """
    Validates completeness and arithmetic correctness according to PRD Section 8.
    Returns (validation_status, list_of_errors) where validation_status is
    'verified' | 'incomplete' | 'mismatch'.
    """
    errors: List[str] = []
    has_arithmetic_mismatch = False
    has_missing_required = False

    # 1. Required fields check
    if not data.vendor_name:
        errors.append("Missing required field: Vendor Name")
        has_missing_required = True

    if not data.invoice_number:
        errors.append("Missing required field: Invoice Number")
        has_missing_required = True

    if not data.invoice_date:
        errors.append("Missing required field: Invoice Date")
        has_missing_required = True

    if data.amount_total <= 0:
        errors.append("Missing or invalid required field: Amount Total must be greater than 0")
        has_missing_required = True

    # 2. Arithmetic validation: Subtotal + Tax = Total
    if data.amount_subtotal > 0 or data.tax_amount > 0:
        expected_total = round(data.amount_subtotal + data.tax_amount, 2)
        diff = abs(expected_total - round(data.amount_total, 2))
        if diff > 0.05:
            has_arithmetic_mismatch = True
            errors.append(
                f"Arithmetic Mismatch: Subtotal ({data.currency} {data.amount_subtotal:,.2f}) + "
                f"Tax ({data.currency} {data.tax_amount:,.2f}) = {data.currency} {expected_total:,.2f}, "
                f"but Grand Total stated is {data.currency} {data.amount_total:,.2f} (difference of {data.currency} {diff:,.2f})"
            )

    # 3. Line items sum check
    if data.line_items:
        items_sum = round(sum(item.line_total for item in data.line_items), 2)
        if data.amount_subtotal > 0 and abs(items_sum - round(data.amount_subtotal, 2)) > 0.05:
            has_arithmetic_mismatch = True
            errors.append(
                f"Line Items Mismatch: Sum of line items ({data.currency} {items_sum:,.2f}) "
                f"does not match Subtotal ({data.currency} {data.amount_subtotal:,.2f})"
            )

        for item in data.line_items:
            expected_line = round(item.quantity * item.unit_price, 2)
            if abs(expected_line - round(item.line_total, 2)) > 0.05:
                has_arithmetic_mismatch = True
                errors.append(
                    f"Item Calculation Error in '{item.description}': "
                    f"Qty {item.quantity} × {item.unit_price} = {expected_line}, but line total is {item.line_total}"
                )

    # Determine overall validation status
    if has_arithmetic_mismatch:
        status = "mismatch"
    elif has_missing_required:
        status = "incomplete"
    else:
        status = "verified"

    return status, errors
