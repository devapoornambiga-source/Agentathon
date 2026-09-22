# Project Requirement Document (PRD)
## Autonomous Invoice Processing Agent

**Version:** 1.0
**Type:** Hackathon MVP
**Status:** Draft

---

## 1. Overview

The Autonomous Invoice Processing Agent is an AI-powered system that ingests invoices (PDF, image, or email attachment), extracts structured data using OCR and document understanding, validates the extracted data, detects duplicates or anomalies, and tracks payment status through to completion.

The goal is to eliminate manual invoice data entry and reduce errors, fraud, and missed payment deadlines for small-to-mid-sized businesses and finance teams.

---

## 2. Problem Statement

Finance and accounts-payable teams manually:
- Read invoices line by line to extract vendor, amount, and due date details
- Cross-check for duplicate submissions
- Track due dates across spreadsheets or email threads
- Manually verify tax and totals for arithmetic errors

This is slow, error-prone, and doesn't scale. There is no lightweight, automated first line of defense that turns an invoice into verified, actionable data within seconds.

---

## 3. Goals & Non-Goals

### Goals (MVP)
- Accept an invoice (PDF/image) as input
- Extract key fields automatically via OCR + LLM-based document understanding
- Validate completeness and arithmetic correctness
- Detect duplicate invoices
- Store structured invoice data
- Track and surface due-date/payment status
- Present a clean, readable summary response per invoice

### Non-Goals (out of scope for MVP)
- Actual payment execution / bank transfers
- Multi-currency conversion
- Full fraud-detection ML model (rule-based checks only for MVP)
- Multi-tenant enterprise access control
- Email inbox integration (can be a stretch goal, not core MVP)

---

## 4. User Personas

| Persona | Need |
|---|---|
| Accounts Payable Clerk | Wants invoices auto-verified without manual data entry |
| Finance Manager | Wants visibility into upcoming/overdue payments |
| Small Business Owner | Wants a simple way to avoid duplicate payments and missed due dates |

---

## 5. System Architecture

```text
Invoice / PDF / Email
        ↓
Invoice Agent (Orchestrator)
        ↓
OCR + Document Understanding Layer
        ↓
Field Extraction
   (Vendor, Invoice No, Date, Amount, Tax, Due Date, Bank Details)
        ↓
Validation Engine
   (Required fields check, totals/tax check)
        ↓
Duplicate & Fraud Check
   (Hash match, invoice number + vendor match, amount anomaly)
        ↓
Storage Layer (Database)
        ↓
Payment Tracker
   (Due date monitoring, status updates, alerts)
```

### Components

1. **Ingestion Layer** — Accepts file upload (PDF/image) or forwarded email attachment.
2. **OCR / Document Understanding Layer** — Converts scanned/image invoices to text; uses a vision-language model or OCR engine (e.g., Tesseract, AWS Textract, or an LLM with vision input) for structured field extraction from unstructured layouts.
3. **Extraction Layer** — Parses OCR output into a structured JSON schema (see Section 7).
4. **Validation Engine** — Rule-based checks for missing fields, tax math, and line-item totals.
5. **Duplicate/Fraud Detector** — Compares new invoice against stored records by vendor + invoice number + amount fingerprint; flags anomalies (e.g., mismatched bank details for a known vendor).
6. **Storage Layer** — Persists structured invoice data (SQL or NoSQL database).
7. **Payment Tracker** — Background job / scheduled check that monitors due dates and raises alerts for upcoming or overdue payments.
8. **Response/Reporting Layer** — Formats a human-readable summary per processed invoice.

---

## 6. Agent Capabilities

| Capability | Description |
|---|---|
| 📄 Multi-format reading | Reads PDFs, images (JPG/PNG), and scanned invoices |
| 🔍 Field extraction | Extracts vendor, invoice number, date, amount, tax, due date, bank details |
| ✅ Completeness check | Flags missing required fields |
| 🔄 Duplicate detection | Detects duplicate invoice submissions |
| 🧮 Arithmetic validation | Verifies totals, tax calculations, and line items |
| 📅 Due date tracking | Tracks and calculates days until/past due |
| 🚨 Alerts | Notifies users of overdue or suspicious invoices |
| 💾 Structured storage | Stores parsed invoice data in a database |

---

## 7. Data Model

### Invoice Record Schema

```json
{
  "invoice_id": "string (internal UUID)",
  "vendor_name": "string",
  "invoice_number": "string",
  "invoice_date": "date",
  "due_date": "date",
  "amount_subtotal": "number",
  "tax_amount": "number",
  "amount_total": "number",
  "currency": "string",
  "bank_details": {
    "account_name": "string",
    "account_number": "string",
    "ifsc_or_swift": "string"
  },
  "line_items": [
    { "description": "string", "quantity": "number", "unit_price": "number", "line_total": "number" }
  ],
  "validation_status": "verified | incomplete | mismatch",
  "duplicate_check": "unique | duplicate",
  "fraud_flag": "boolean",
  "payment_status": "pending | due_soon | overdue | paid",
  "source_file": "string (path/reference)",
  "created_at": "timestamp"
}
```

---

## 8. Core Workflow

1. User uploads an invoice file.
2. Agent runs OCR/document understanding to extract raw text and layout.
3. Agent maps extracted text to the structured schema above.
4. Validation engine checks:
   - Are all required fields present?
   - Does subtotal + tax = total?
   - Do line-item totals sum to the subtotal?
5. Duplicate check compares (vendor + invoice number + amount) against existing records.
6. If bank details differ from a previously stored vendor record, flag as a fraud risk.
7. Record is stored with a validation and duplicate status.
8. Payment tracker calculates days remaining until due date (or overdue days).
9. Agent returns a structured summary response to the user.

---

## 9. Example Output

**Input:** `invoice_1024.pdf`

```text
Vendor: ABC Suppliers
Invoice: INV-1024
Amount: ₹84,500
Due: 30 Sept 2026
Status: Verified
Duplicate: No
Payment: Due in 9 days
```

---

## 10. MVP Scope (Hackathon Build)

### Must-Have (Day 1 build target)
- File upload (PDF/image) UI
- OCR/LLM-based extraction of core fields
- Basic validation (required fields + totals check)
- Duplicate detection via simple hash/lookup
- Structured storage (SQLite or a lightweight cloud DB)
- Summary response view per invoice

### Should-Have (if time permits)
- Dashboard listing all invoices with status filters (verified/duplicate/overdue)
- Due-date alert banner or notification
- Basic fraud flag on bank-detail mismatch

### Stretch Goals
- Email ingestion (forward invoice to an inbox, auto-process)
- Multi-currency support
- Export to CSV/Excel for accounting software
- Slack/WhatsApp alert integration for overdue invoices

---

## 11. Tech Stack (Suggested)

| Layer | Suggested Tools |
|---|---|
| OCR / Extraction | Tesseract OCR, AWS Textract, or an LLM with vision capabilities (e.g., Claude, GPT-4V) |
| Backend | Python (FastAPI) or Node.js (Express) |
| Database | SQLite (hackathon) / PostgreSQL (production) |
| Frontend | React or a simple HTML/JS dashboard |
| File Storage | Local disk (hackathon) / S3 or equivalent (production) |
| Scheduler (due-date checks) | Cron job or a simple background worker |

---

## 12. Success Metrics

- **Extraction accuracy:** % of fields correctly extracted vs. ground truth
- **Processing time:** Average time from upload to structured summary
- **Duplicate detection precision:** False positive/negative rate
- **Validation coverage:** % of invoices correctly flagged for missing/mismatched data

---

## 13. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Poor OCR accuracy on low-quality scans | Use a vision-capable LLM as fallback for messy layouts |
| False duplicate flags (similar invoices, different vendors) | Use composite key (vendor + invoice number + amount + date) instead of single-field match |
| Fraud detection false positives | Keep fraud check as advisory ("flagged for review"), not auto-block, in MVP |
| Time constraints in hackathon | Prioritize Must-Have scope; treat dashboard/alerts as stretch |

---

## 14. Team Roles (Suggested for Hackathon)

| Role | Responsibility |
|---|---|
| Backend/AI Engineer | OCR integration, extraction pipeline, validation logic |
| Frontend Developer | Upload UI, dashboard, summary display |
| Data/Backend Support | Database schema, duplicate-check logic, storage |
| Presenter/PM | Demo flow, pitch narrative, edge-case testing |

---

## 15. Demo Flow (Suggested)

1. Upload a sample invoice PDF live.
2. Show extracted structured data appearing within seconds.
3. Upload the same invoice again → show duplicate detection catching it.
4. Upload an invoice with a deliberately wrong tax total → show validation flag.
5. Show the due-date tracker with a "Due in X days" / "Overdue" status.
