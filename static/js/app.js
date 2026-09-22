// Autonomous Invoice Processing Agent - Client Application Logic

let currentFilter = 'all';
let currentSearch = '';
let activeRecord = null;

document.addEventListener('DOMContentLoaded', () => {
  initDropzone();
  loadKpis();
  loadInvoices();
});

// --- Ingestion & Dropzone Setup ---
function initDropzone() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');

  dropzone.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });
}

// --- Upload Processing ---
async function uploadFile(file) {
  const progress = document.getElementById('upload-progress');
  const dropzoneIcon = document.getElementById('dropzone-icon');
  
  progress.style.display = 'block';
  dropzoneIcon.style.opacity = '0.3';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/invoices/upload', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Upload failed');
    }

    const record = await res.json();
    displayRecord(record);
    showToast(`Invoice ${record.invoice_number || file.name} processed successfully!`, 'success');
    loadKpis();
    loadInvoices();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  } finally {
    progress.style.display = 'none';
    dropzoneIcon.style.opacity = '1';
    document.getElementById('file-input').value = '';
  }
}

// --- Run Demo Sample Invoice ---
async function runSample(sampleFilename) {
  const progress = document.getElementById('upload-progress');
  progress.style.display = 'block';

  try {
    const res = await fetch(`/api/samples/process/${encodeURIComponent(sampleFilename)}`, {
      method: 'POST'
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Sample run failed');
    }

    const record = await res.json();
    displayRecord(record);
    showToast(`Processed sample ${sampleFilename}`, 'success');
    loadKpis();
    loadInvoices();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  } finally {
    progress.style.display = 'none';
  }
}

// --- Display Record in Inspection Panel ---
function displayRecord(record) {
  activeRecord = record;

  // 1. Status Badge
  const statusBadge = document.getElementById('active-status-badge');
  if (record.fraud_flag) {
    statusBadge.className = 'scenario-badge badge-fraud';
    statusBadge.textContent = '🚨 Fraud Risk';
  } else if (record.duplicate_check === 'duplicate') {
    statusBadge.className = 'scenario-badge badge-duplicate';
    statusBadge.textContent = '🔁 Duplicate';
  } else if (record.validation_status === 'verified') {
    statusBadge.className = 'scenario-badge badge-verified';
    statusBadge.textContent = '✓ Verified';
  } else if (record.validation_status === 'mismatch') {
    statusBadge.className = 'scenario-badge badge-mismatch';
    statusBadge.textContent = '⚠️ Mismatch';
  } else {
    statusBadge.className = 'scenario-badge badge-incomplete';
    statusBadge.textContent = 'Incomplete';
  }

  // 2. Alert Banners
  const alertContainer = document.getElementById('alert-container');
  let alertsHtml = '';

  if (record.fraud_flag && record.fraud_reason) {
    alertsHtml += `
      <div class="alert-banner alert-fraud">
        <span style="font-size: 1.2rem;">🚨</span>
        <div>
          <strong>CRITICAL FRAUD RISK DETECTED</strong>
          <div>${record.fraud_reason}</div>
        </div>
      </div>
    `;
  }

  if (record.duplicate_check === 'duplicate') {
    alertsHtml += `
      <div class="alert-banner alert-duplicate">
        <span style="font-size: 1.2rem;">🔁</span>
        <div>
          <strong>DUPLICATE INVOICE DETECTED</strong>
          <div>This invoice matches a previously ingested record (Original ID: ${record.duplicate_of_id || 'Matched'}).</div>
        </div>
      </div>
    `;
  }

  if (record.validation_status === 'mismatch' && record.validation_errors.length > 0) {
    alertsHtml += `
      <div class="alert-banner alert-mismatch">
        <span style="font-size: 1.2rem;">⚠️</span>
        <div>
          <strong>ARITHMETIC VALIDATION MISMATCH</strong>
          <ul style="margin-left: 18px; margin-top: 4px;">
            ${record.validation_errors.map(e => `<li>${e}</li>`).join('')}
          </ul>
        </div>
      </div>
    `;
  }

  alertContainer.innerHTML = alertsHtml;

  // 3. PRD Section 9 Summary Text
  const summaryBox = document.getElementById('summary-box-content');
  summaryBox.textContent = record.summary_text || 'No summary generated.';

  // 4. Extracted Key-Values
  const curr = record.currency === 'INR' ? '₹' : (record.currency === 'USD' ? '$' : record.currency + ' ');
  document.getElementById('detail-vendor').textContent = record.vendor_name || 'N/A';
  document.getElementById('detail-invoice-num').textContent = record.invoice_number || 'N/A';
  document.getElementById('detail-date').textContent = record.invoice_date || 'N/A';
  document.getElementById('detail-due-date').textContent = record.due_date || 'N/A';
  document.getElementById('detail-subtotal').textContent = `${curr}${record.amount_subtotal.toLocaleString()}`;
  document.getElementById('detail-tax').textContent = `${curr}${record.tax_amount.toLocaleString()}`;
  document.getElementById('detail-total').textContent = `${curr}${record.amount_total.toLocaleString()}`;
  
  const bank = record.bank_details;
  if (bank && (bank.account_number || bank.ifsc_or_swift)) {
    document.getElementById('detail-bank').textContent = `A/C: ${bank.account_number || 'N/A'} | IFSC: ${bank.ifsc_or_swift || 'N/A'}`;
  } else {
    document.getElementById('detail-bank').textContent = 'None detected';
  }

  // 5. Line Items Table
  const tbody = document.getElementById('line-items-tbody');
  if (record.line_items && record.line_items.length > 0) {
    tbody.innerHTML = record.line_items.map(item => `
      <tr>
        <td><strong>${item.description}</strong></td>
        <td>${item.quantity}</td>
        <td>${curr}${item.unit_price.toLocaleString()}</td>
        <td style="font-weight: 600;">${curr}${item.line_total.toLocaleString()}</td>
      </tr>
    `).join('');
  } else {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No line items detected</td></tr>';
  }

  // 6. JSON Viewer
  document.getElementById('json-viewer-content').textContent = JSON.stringify(record, null, 2);
}

// --- Tab Switching ---
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

  if (tabId === 'tab-summary') document.getElementById('btn-tab-summary').classList.add('active');
  if (tabId === 'tab-details') document.getElementById('btn-tab-details').classList.add('active');
  if (tabId === 'tab-items') document.getElementById('btn-tab-items').classList.add('active');
  if (tabId === 'tab-json') document.getElementById('btn-tab-json').classList.add('active');

  const content = document.getElementById(tabId);
  if (content) content.classList.add('active');
}

function copySummary() {
  const text = document.getElementById('summary-box-content').textContent;
  navigator.clipboard.writeText(text).then(() => {
    showToast('Summary copied to clipboard!', 'success');
  });
}

// --- Load KPIs ---
async function loadKpis() {
  try {
    const res = await fetch('/api/kpis');
    if (!res.ok) return;
    const kpi = await res.json();

    document.getElementById('kpi-total-count').textContent = kpi.total_count;
    document.getElementById('kpi-total-amount').textContent = `₹${kpi.total_amount.toLocaleString()} cumulative spend`;
    document.getElementById('kpi-verified-count').textContent = kpi.verified_count;
    document.getElementById('kpi-duplicate-count').textContent = kpi.duplicate_count;
    document.getElementById('kpi-fraud-count').textContent = kpi.fraud_count;
    document.getElementById('kpi-overdue-count').textContent = kpi.overdue_count;
  } catch (e) {
    console.error('Failed to load KPIs:', e);
  }
}

// --- Load Invoices Ledger ---
async function loadInvoices() {
  try {
    let url = '/api/invoices?';
    if (currentFilter && currentFilter !== 'all') {
      url += `status=${encodeURIComponent(currentFilter)}&`;
    }
    if (currentSearch) {
      url += `search=${encodeURIComponent(currentSearch)}&`;
    }

    const res = await fetch(url);
    if (!res.ok) return;
    const invoices = await res.json();

    const tbody = document.getElementById('invoices-tbody');
    if (invoices.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 28px; color: var(--text-muted);">No matching invoices found in database.</td></tr>';
      return;
    }

    tbody.innerHTML = invoices.map(inv => {
      const curr = inv.currency === 'INR' ? '₹' : (inv.currency === 'USD' ? '$' : inv.currency + ' ');
      
      // Validation Badge
      let valBadge = `<span class="scenario-badge badge-verified">Verified</span>`;
      if (inv.validation_status === 'mismatch') valBadge = `<span class="scenario-badge badge-mismatch">Mismatch</span>`;
      else if (inv.validation_status === 'incomplete') valBadge = `<span class="scenario-badge badge-incomplete">Incomplete</span>`;

      // Security Badges
      let secBadges = '';
      if (inv.duplicate_check === 'duplicate') {
        secBadges += `<span class="scenario-badge badge-duplicate" title="Duplicate of ${inv.duplicate_of_id}">Duplicate</span> `;
      }
      if (inv.fraud_flag) {
        secBadges += `<span class="scenario-badge badge-fraud" title="${inv.fraud_reason}">🚨 Fraud Risk</span> `;
      }
      if (!secBadges) {
        secBadges = `<span style="color: var(--text-muted); font-size: 0.8rem;">Clean</span>`;
      }

      // Payment Countdown Chip
      let payChip = '';
      if (inv.payment_status === 'paid') {
        payChip = `<span class="scenario-badge badge-paid">Paid</span>`;
      } else if (inv.payment_status === 'overdue') {
        payChip = `<span class="scenario-badge badge-overdue">Overdue (${Math.abs(inv.days_due)}d)</span>`;
      } else if (inv.payment_status === 'due_soon') {
        payChip = `<span class="scenario-badge badge-duplicate">Due soon (${inv.days_due}d)</span>`;
      } else {
        payChip = `<span class="scenario-badge badge-incomplete">Due in ${inv.days_due}d</span>`;
      }

      return `
        <tr>
          <td>
            <strong>${inv.vendor_name || 'Unknown Vendor'}</strong>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${inv.source_file || 'manual'}</div>
          </td>
          <td>
            <code>${inv.invoice_number || 'N/A'}</code>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${inv.invoice_date || 'No date'}</div>
          </td>
          <td>
            <div>${inv.due_date || '—'}</div>
            <div style="margin-top: 4px;">${payChip}</div>
          </td>
          <td style="font-weight: 700; color: #ffffff;">${curr}${inv.amount_total.toLocaleString()}</td>
          <td>${valBadge}</td>
          <td>${secBadges}</td>
          <td>
            ${inv.payment_status === 'paid' 
              ? `<span style="color: var(--accent-emerald); font-size: 0.85rem;">✓ Completed</span>` 
              : `<button class="btn btn-outline" style="padding: 4px 10px; font-size: 0.78rem;" onclick="markPaid('${inv.invoice_id}')">Mark Paid</button>`
            }
          </td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-outline" style="padding: 4px 8px; font-size: 0.78rem;" onclick='inspectInvoice(${JSON.stringify(inv)})' title="View in Diagnostics">🔍</button>
              <button class="btn btn-outline" style="padding: 4px 8px; font-size: 0.78rem; color: var(--accent-rose);" onclick="deleteInvoiceRecord('${inv.invoice_id}')" title="Delete">🗑️</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // If first load and no active record, select top invoice
    if (!activeRecord && invoices.length > 0) {
      displayRecord(invoices[0]);
    }
  } catch (e) {
    console.error('Failed to load invoices:', e);
  }
}

function inspectInvoice(inv) {
  displayRecord(inv);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function markPaid(invoiceId) {
  try {
    const res = await fetch(`/api/invoices/${invoiceId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ payment_status: 'paid' })
    });
    if (res.ok) {
      showToast('Invoice marked as Paid!', 'success');
      loadKpis();
      loadInvoices();
    }
  } catch (e) {
    showToast('Failed to update status', 'error');
  }
}

async function deleteInvoiceRecord(invoiceId) {
  if (!confirm('Are you sure you want to delete this invoice record?')) return;
  try {
    const res = await fetch(`/api/invoices/${invoiceId}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('Invoice deleted', 'success');
      loadKpis();
      loadInvoices();
    }
  } catch (e) {
    showToast('Failed to delete invoice', 'error');
  }
}

function setFilter(filter) {
  currentFilter = filter;
  document.querySelectorAll('.filter-pill').forEach(btn => {
    btn.classList.toggle('active', btn.textContent.toLowerCase().includes(filter) || (filter === 'all' && btn.textContent === 'All'));
  });
  loadInvoices();
}

let searchDebounce = null;
function handleSearch() {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    currentSearch = document.getElementById('search-input').value.trim();
    loadInvoices();
  }, 250);
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  const icon = type === 'success' ? '✓' : (type === 'error' ? '⚠️' : 'ℹ️');
  toast.innerHTML = `<span style="color: ${type === 'success' ? '#10b981' : (type === 'error' ? '#f43f5e' : '#38bdf8')}; font-weight: 700;">${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}
