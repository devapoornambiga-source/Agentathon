import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import uvicorn
from app.database import init_db
from app.sample_generator import generate_all_samples

if __name__ == "__main__":
    print("==================================================")
    print("  STARTING AUTONOMOUS INVOICE AGENT SERVER        ")
    print("==================================================")
    print("1. Initializing database schema...")
    init_db()
    print("2. Generating sample demo invoices for testing...")
    samples = generate_all_samples()
    print(f"   Generated {len(samples)} sample files ready in sample_invoices/.")
    print("3. Launching FastAPI server on http://127.0.0.1:8000 ...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
