import csv
import io
import os
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

from app.config import UPLOAD_DIR, SAMPLES_DIR, BASE_DIR
from app.database import (
    init_db,
    save_invoice,
    get_invoice,
    list_invoices,
    update_payment_status,
    delete_invoice,
    get_kpis
)
from app.models import InvoiceRecord
from app.agent.orchestrator import process_invoice_file
from app.sample_generator import SAMPLE_DEFINITIONS, generate_all_samples

app = FastAPI(
    title="Autonomous Invoice Processing Agent",
    description="AI-powered invoice ingestion, OCR/document understanding, validation, duplicate & fraud detection, and payment tracking.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    init_db()
    generate_all_samples()


# --- API Endpoints ---

@app.post("/api/invoices/upload", response_model=InvoiceRecord)
async def upload_invoice(file: UploadFile = File(...)):
    """Upload and process an invoice (PDF, image, text)."""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Save to upload folder
    saved_path = UPLOAD_DIR / file.filename
    saved_path.write_bytes(file_bytes)

    # Run agent orchestrator
    record = process_invoice_file(saved_path, file_bytes, source_filename=file.filename)
    return record


@app.get("/api/invoices", response_model=List[InvoiceRecord])
def get_all_invoices(
    status: Optional[str] = Query(None, description="Filter by status (verified, incomplete, mismatch, duplicate, fraud, overdue, due_soon, paid)"),
    search: Optional[str] = Query(None, description="Search by vendor or invoice number")
):
    """Retrieve invoices with optional filtering and search."""
    return list_invoices(status_filter=status, search=search)


@app.get("/api/invoices/{invoice_id}", response_model=InvoiceRecord)
def get_single_invoice(invoice_id: str):
    record = get_invoice(invoice_id)
    if not record:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return record


class StatusUpdateRequest(BaseModel):
    payment_status: str


@app.patch("/api/invoices/{invoice_id}/status")
def update_status(invoice_id: str, payload: StatusUpdateRequest):
    success = update_payment_status(invoice_id, payload.payment_status)
    if not success:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": "Status updated successfully", "invoice_id": invoice_id, "new_status": payload.payment_status}


@app.delete("/api/invoices/{invoice_id}")
def remove_invoice(invoice_id: str):
    success = delete_invoice(invoice_id)
    if not success:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": "Invoice deleted successfully"}


@app.get("/api/kpis")
def get_kpi_metrics():
    return get_kpis()


@app.get("/api/samples")
def list_sample_invoices():
    """List pre-configured demo invoices for 1-click testing."""
    samples = []
    for filename, meta in SAMPLE_DEFINITIONS.items():
        file_path = SAMPLES_DIR / filename
        samples.append({
            "filename": filename,
            "title": meta["title"],
            "scenario": meta["scenario"],
            "description": meta["description"],
            "exists": file_path.exists()
        })
    return samples


@app.post("/api/samples/process/{sample_name}", response_model=InvoiceRecord)
def process_sample(sample_name: str):
    file_path = SAMPLES_DIR / sample_name
    if not file_path.exists():
        # regenerate if missing
        generate_all_samples()
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Sample file {sample_name} not found")

    file_bytes = file_path.read_bytes()
    record = process_invoice_file(file_path, file_bytes, source_filename=sample_name)
    return record


@app.get("/api/export/csv")
def export_invoices_csv():
    """Export all stored invoice records to CSV format."""
    invoices = list_invoices()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Invoice ID", "Vendor Name", "Invoice Number", "Invoice Date", "Due Date",
        "Subtotal", "Tax", "Total Amount", "Currency", "Validation Status",
        "Duplicate Check", "Fraud Flag", "Payment Status", "Days Due", "Created At"
    ])

    for inv in invoices:
        writer.writerow([
            inv.invoice_id,
            inv.vendor_name,
            inv.invoice_number,
            inv.invoice_date,
            inv.due_date,
            inv.amount_subtotal,
            inv.tax_amount,
            inv.amount_total,
            inv.currency,
            inv.validation_status,
            inv.duplicate_check,
            "YES" if inv.fraud_flag else "NO",
            inv.payment_status,
            inv.days_due,
            inv.created_at
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices_ledger_export.csv"}
    )


# --- Static Files Mount ---
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def serve_frontend():
        index_file = static_dir / "index.html"
        if index_file.exists():
            return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Autonomous Invoice Agent API Running</h1><p>Frontend file static/index.html not found.</p>")
