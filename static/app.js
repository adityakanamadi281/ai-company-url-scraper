/* Company Intelligence Scraper — frontend logic */

const $ = id => document.getElementById(id);

// ── State ─────────────────────────────────────────────────────────────────
let currentView = 'cards';

// ── DOM refs ─────────────────────────────────────────────────────────────
const urlInput    = $('urlInput');
const enrichBtn   = $('enrichBtn');
const resultCard  = $('resultCard');
const errorBox    = $('errorBox');
const tableView   = $('tableView');
const cardsView   = $('cardsView');
const countBadge  = $('countBadge');
const tableBody   = $('tableBody');
const cardsGrid   = $('cardsGrid');

// ── Enrich ────────────────────────────────────────────────────────────────
enrichBtn.addEventListener('click', async () => {
  const url = urlInput.value.trim();
  if (!url) { showError('Please enter a company URL.'); return; }

  setLoading(true);
  hideError();
  resultCard.classList.remove('visible');

  try {
    const res = await fetch('/enrich', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);

    renderResultCard(data);
    resultCard.classList.add('visible');
    await loadResults();
  } catch (err) {
    showError(err.message || 'Enrichment failed. Check your URL and Gemini API key.');
  } finally {
    setLoading(false);
  }
});

urlInput.addEventListener('keydown', e => { if (e.key === 'Enter') enrichBtn.click(); });

// ── Result card ───────────────────────────────────────────────────────────
function renderResultCard(d) {
  resultCard.innerHTML = `
    <div class="field-row">
      <div class="field-label">Company</div>
      <div class="field-value big">${esc(d.company_name || d.website_name || '—')}</div>
    </div>
    <div class="field-row">
      <div class="field-label">Website</div>
      <div class="field-value">${esc(d.website_name || '—')}</div>
    </div>
    ${d.core_service ? `
    <div class="field-row">
      <div class="field-label">Core Service</div>
      <div class="field-value">${esc(d.core_service)}</div>
    </div>` : ''}
    ${d.target_customer ? `
    <div class="field-row">
      <div class="field-label">Target Customer</div>
      <div class="field-value">${esc(d.target_customer)}</div>
    </div>` : ''}
    ${d.probable_pain_point ? `
    <div class="field-row">
      <div class="field-label">Pain Point Solved</div>
      <div class="field-value">${esc(d.probable_pain_point)}</div>
    </div>` : ''}
    ${d.address ? `
    <div class="field-row">
      <div class="field-label">Address</div>
      <div class="field-value">${esc(d.address)}</div>
    </div>` : ''}
    ${d.mobile_number ? `
    <div class="field-row">
      <div class="field-label">Phone</div>
      <div class="field-value">${esc(d.mobile_number)}</div>
    </div>` : ''}
    ${d.mail && d.mail.length ? `
    <div class="field-row">
      <div class="field-label">Email(s)</div>
      <div class="mail-pills">${d.mail.map(m => `<span class="mail-pill">${esc(m)}</span>`).join('')}</div>
    </div>` : ''}
    ${d.outreach_opener ? `
    <div class="field-row">
      <div class="field-label">Outreach Opener</div>
      <div class="outreach-box">${esc(d.outreach_opener)}</div>
    </div>` : ''}
  `;
}

// ── Load all results ──────────────────────────────────────────────────────
async function loadResults() {
  try {
    const res = await fetch('/results');
    const data = await res.json();
    countBadge.textContent = `${data.length} record${data.length !== 1 ? 's' : ''}`;

    if (data.length === 0) {
      tableView.innerHTML = emptyState();
      cardsView.innerHTML = emptyState();
      return;
    }

    renderTable(data);
    renderCards(data);
  } catch (err) {
    console.error('Failed to load results:', err);
  }
}

function renderTable(companies) {
  tableView.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Website</th>
            <th>Core Service</th>
            <th>Email(s)</th>
            <th>Phone</th>
            <th>Address</th>
            <th>Indexed</th>
          </tr>
        </thead>
        <tbody id="tableBody">
          ${companies.map(d => `
          <tr>
            <td><strong>${esc(d.company_name || d.website_name || '—')}</strong><br>
              <span class="url-cell">${esc(d.url || '')}</span></td>
            <td>${esc(d.website_name || '—')}</td>
            <td class="service-cell">${esc(d.core_service || '—')}</td>
            <td>${d.mail && d.mail.length
              ? `<div class="mail-pills">${d.mail.map(m => `<span class="mail-pill">${esc(m)}</span>`).join('')}</div>`
              : '<span style="color:var(--muted)">—</span>'}</td>
            <td>${esc(d.mobile_number || '—')}</td>
            <td>${esc(d.address || '—')}</td>
            <td style="color:var(--muted);font-family:var(--mono);font-size:0.72rem">${(d.created_at || '').slice(0, 10)}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
}

function renderCards(companies) {
  cardsView.innerHTML = `<div class="cards-grid">${companies.map(d => `
    <div class="company-card">
      <div class="card-company">${esc(d.company_name || d.website_name || '—')}</div>
      <div class="card-url">${esc(d.url || '')}</div>

      ${field('Website', d.website_name)}
      ${field('Core Service', d.core_service)}
      ${field('Target Customer', d.target_customer)}
      ${field('Pain Point', d.probable_pain_point)}
      ${field('Address', d.address)}
      ${field('Phone', d.mobile_number)}

      ${d.mail && d.mail.length ? `
      <div class="card-section">
        <div class="field-label">Email(s)</div>
        <div class="mail-pills">${d.mail.map(m => `<span class="mail-pill">${esc(m)}</span>`).join('')}</div>
      </div>` : ''}

      ${d.outreach_opener ? `
      <div class="card-section">
        <div class="field-label">Outreach Opener</div>
        <div class="outreach-box">${esc(d.outreach_opener)}</div>
      </div>` : ''}
    </div>`).join('')}</div>`;
}

// ── View toggle ───────────────────────────────────────────────────────────
window.toggleView = function(mode) {
  currentView = mode;
  $('btnTable').classList.toggle('active', mode === 'table');
  $('btnCards').classList.toggle('active', mode === 'cards');
  tableView.classList.toggle('hidden', mode !== 'table');
  cardsView.classList.toggle('hidden', mode !== 'cards');
};

// ── Helpers ───────────────────────────────────────────────────────────────
function setLoading(on) {
  enrichBtn.classList.toggle('loading', on);
  enrichBtn.disabled = on;
}

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.classList.add('visible');
}

function hideError() {
  errorBox.classList.remove('visible');
}

function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function field(label, value) {
  if (!value) return '';
  return `<div class="card-section">
    <div class="field-label">${label}</div>
    <div class="field-value">${esc(value)}</div>
  </div>`;
}

function emptyState() {
  return `<div class="empty-state"><div class="icon">◎</div><p>No companies enriched yet. Submit a URL above.</p></div>`;
}

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  toggleView('cards');
  loadResults();
});
