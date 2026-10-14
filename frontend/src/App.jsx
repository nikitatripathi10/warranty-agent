import { useState, useEffect, useRef } from 'react'
import './index.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// ── Formatters ─────────────────────────────────────────────────────────────────

function fmt(value, fallback = '—') {
  if (value === null || value === undefined || value === '') return fallback
  return String(value)
}

function fmtPrice(price) {
  if (!price) return '—'
  return `₹${Number(price).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
}

function fmtDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function daysUntil(dateStr) {
  if (!dateStr) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr + 'T00:00:00')
  return Math.round((target - today) / 86400000)
}

function urgencyColor(days) {
  if (days === null) return ''
  if (days < 0) return 'overdue'
  if (days <= 7) return 'critical'
  if (days <= 30) return 'warning'
  return 'safe'
}

function urgencyLabel(days, type) {
  if (days === null) return null
  if (days < 0) return `${type} expired ${Math.abs(days)} days ago`
  if (days === 0) return `${type} expires today!`
  if (days === 1) return `${type} expires tomorrow`
  return `${type} expires in ${days} days`
}

// ── Small components ──────────────────────────────────────────────────────────

function StatusBadge({ status }) {
  if (status === 'checking') {
    return (
      <span className="status-pill loading">
        <span className="spinner" style={{ width: 10, height: 10, borderWidth: 1.5 }} />
        Connecting…
      </span>
    )
  }
  if (status === 'ok') {
    return (
      <span className="status-pill ok">
        <span className="status-dot" />
        All Systems Operational
      </span>
    )
  }
  return (
    <span className="status-pill error">
      <span className="status-dot" />
      Service Unavailable
    </span>
  )
}

function ConfidenceBadge({ confidence }) {
  const labels = { high: 'High', medium: 'Moderate', low: 'Low' }
  return (
    <span className={`confidence-badge ${confidence}`}>
      {labels[confidence] || confidence}
    </span>
  )
}

function UserChip({ email }) {
  const initials = email ? email.slice(0, 2).toUpperCase() : '?'
  return (
    <span className="user-chip">
      <span className="user-chip-avatar">{initials}</span>
      {email}
    </span>
  )
}

function UrgencyChip({ days, label }) {
  const cls = urgencyColor(days)
  if (days === null) return null
  return <span className={`urgency-chip ${cls}`}>{label}</span>
}

function AlertTypeIcon({ type }) {
  const icons = {
    return_window_expiry: '🔄',
    warranty_expiry: '🛡️',
    recall: '⚠️',
  }
  return <span>{icons[type] || '🔔'}</span>
}

function AlertTypeName({ type }) {
  const names = {
    return_window_expiry: 'Return Window',
    warranty_expiry: 'Warranty Expiry',
    recall: 'Product Recall',
  }
  return <>{names[type] || type}</>
}

// ── Product card for dashboard ────────────────────────────────────────────────

function PurchaseCard({ purchase, onSelect }) {
  const wp = purchase.warranty_period
  const returnDays = wp?.return_window_end_date ? daysUntil(wp.return_window_end_date) : null
  const warrantyDays = wp?.warranty_end_date ? daysUntil(wp.warranty_end_date) : null

  const urgentDays = [returnDays, warrantyDays].filter(d => d !== null)
  const mostUrgent = urgentDays.length > 0 ? Math.min(...urgentDays) : null
  const cardClass = mostUrgent !== null ? `purchase-card ${urgencyColor(mostUrgent)}` : 'purchase-card'

  return (
    <div className={cardClass} onClick={() => onSelect(purchase)} role="button" tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onSelect(purchase)}>
      <div className="purchase-card-header">
        <div className="purchase-card-icon">
          {purchase.source_type === 'email' ? '📧' : '📄'}
        </div>
        <div className="purchase-card-retailer">{fmt(purchase.retailer || purchase.brand, 'Unknown Retailer')}</div>
        <ConfidenceBadge confidence={wp?.confidence_score || 'low'} />
      </div>
      <div className="purchase-card-product">{fmt(purchase.product_name, 'Unnamed Product')}</div>
      <div className="purchase-card-meta">
        <span>🗓 {fmtDate(purchase.purchase_date)}</span>
        {purchase.price && <span>💰 {fmtPrice(purchase.price)}</span>}
      </div>
      {mostUrgent !== null && (
        <div className="purchase-card-urgency">
          {returnDays !== null && (
            <UrgencyChip days={returnDays} label={urgencyLabel(returnDays, 'Return')} />
          )}
          {warrantyDays !== null && (
            <UrgencyChip days={warrantyDays} label={urgencyLabel(warrantyDays, 'Warranty')} />
          )}
          {wp?.is_estimated && <span className="estimated-badge">Estimated</span>}
        </div>
      )}
    </div>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  // Auth state
  const [userId, setUserId] = useState(() => localStorage.getItem('wrd_user_id') || '')
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem('wrd_user_email') || '')
  const isConnected = Boolean(userId && userEmail)

  // Navigation
  const [screen, setScreen] = useState('connect') // connect | dashboard | detail | alerts | upload | lookup

  // Health
  const [healthStatus, setHealthStatus] = useState('checking')

  // Purchases list
  const [purchases, setPurchases] = useState([])
  const [purchasesLoading, setPurchasesLoading] = useState(false)
  const [purchasesError, setPurchasesError] = useState(null)
  const [selectedPurchase, setSelectedPurchase] = useState(null)

  // Edit modal
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState({})
  const [editLoading, setEditLoading] = useState(false)
  const [editError, setEditError] = useState(null)

  // Alerts
  const [alerts, setAlerts] = useState([])
  const [alertsLoading, setAlertsLoading] = useState(false)

  // Upload
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const [dragover, setDragover] = useState(false)

  // Fetch emails
  const [fetchLoading, setFetchLoading] = useState(false)
  const [fetchResult, setFetchResult] = useState(null)
  const [fetchError, setFetchError] = useState(null)

  // Quick lookup
  const [testText, setTestText] = useState('')
  const [testLoading, setTestLoading] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testError, setTestError] = useState(null)

  // Agent chat
  const [agentQuestion, setAgentQuestion] = useState('')
  const [agentAnswer, setAgentAnswer] = useState(null)
  const [agentLoading, setAgentLoading] = useState(false)

  const fileInputRef = useRef(null)

  // ── Boot effects ──────────────────────────────────────────────────────────
  useEffect(() => {
    // Handle OAuth callback params
    const params = new URLSearchParams(window.location.search)
    const cbUserId = params.get('user_id')
    const cbEmail = params.get('email')
    if (cbUserId && cbEmail) {
      localStorage.setItem('wrd_user_id', cbUserId)
      localStorage.setItem('wrd_user_email', cbEmail)
      setUserId(cbUserId)
      setUserEmail(cbEmail)
      window.history.replaceState({}, '', '/')
    }

    // Health check
    fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) })
      .then(r => r.ok ? setHealthStatus('ok') : setHealthStatus('error'))
      .catch(() => setHealthStatus('error'))
  }, [])

  useEffect(() => {
    if (isConnected) {
      setScreen('dashboard')
      loadPurchases()
      loadAlerts()
    } else {
      setScreen('connect')
    }
  }, [isConnected]) // eslint-disable-line

  // ── API functions ─────────────────────────────────────────────────────────
  async function loadPurchases() {
    setPurchasesLoading(true)
    setPurchasesError(null)
    try {
      const res = await fetch(`${API_BASE}/purchases?user_id=${encodeURIComponent(userId)}`)
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setPurchases(data.purchases || [])
    } catch (err) {
      setPurchasesError(err.message)
    } finally {
      setPurchasesLoading(false)
    }
  }

  async function loadAlerts() {
    setAlertsLoading(true)
    try {
      const res = await fetch(`${API_BASE}/alerts?user_id=${encodeURIComponent(userId)}&days_ahead=60`)
      const data = await res.json()
      if (res.ok) setAlerts(data.alerts || [])
    } catch { /* silent */ }
    finally { setAlertsLoading(false) }
  }

  async function handleFetchEmails() {
    if (!userId) return
    setFetchLoading(true)
    setFetchResult(null)
    setFetchError(null)
    try {
      const res = await fetch(
        `${API_BASE}/ingestion/fetch-emails?user_id=${encodeURIComponent(userId)}&max_results=25`,
        { method: 'POST', signal: AbortSignal.timeout(120000) }
      )
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setFetchResult(data)
      loadPurchases()
      loadAlerts()
    } catch (err) {
      setFetchError(err.message)
    } finally {
      setFetchLoading(false)
    }
  }

  async function handleUpload() {
    if (!uploadFile || !userId) return
    setUploadLoading(true)
    setUploadResult(null)
    setUploadError(null)
    const formData = new FormData()
    formData.append('file', uploadFile)
    formData.append('user_id', userId)
    try {
      const res = await fetch(`${API_BASE}/ingestion/upload`, {
        method: 'POST', body: formData, signal: AbortSignal.timeout(60000),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setUploadResult(data)
      loadPurchases()
      loadAlerts()
    } catch (err) {
      setUploadError(err.message)
    } finally {
      setUploadLoading(false)
    }
  }

  async function handleExtractionTest() {
    if (!testText.trim()) return
    setTestLoading(true)
    setTestResult(null)
    setTestError(null)
    try {
      const res = await fetch(`${API_BASE}/extraction/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: testText }),
        signal: AbortSignal.timeout(45000),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setTestResult(data)
    } catch (err) {
      setTestError(err.message)
    } finally {
      setTestLoading(false)
    }
  }

  async function handleSaveEdit() {
    setEditLoading(true)
    setEditError(null)
    // Build request body with only changed / non-empty fields
    const body = {}
    if (editForm.product_name !== undefined) body.product_name = editForm.product_name
    if (editForm.brand !== undefined) body.brand = editForm.brand
    if (editForm.retailer !== undefined) body.retailer = editForm.retailer
    if (editForm.purchase_date !== undefined) body.purchase_date = editForm.purchase_date || null
    if (editForm.price !== undefined) body.price = editForm.price ? parseFloat(editForm.price) : null
    if (editForm.warranty_end_date !== undefined) body.warranty_end_date = editForm.warranty_end_date || null
    if (editForm.return_window_end_date !== undefined) body.return_window_end_date = editForm.return_window_end_date || null
    if (editForm.family_member !== undefined) body.family_member = editForm.family_member || null

    try {
      const res = await fetch(
        `${API_BASE}/purchases/${selectedPurchase.id}?user_id=${encodeURIComponent(userId)}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }
      )
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setSelectedPurchase(data)
      setEditMode(false)
      loadPurchases()
      loadAlerts()
    } catch (err) {
      setEditError(err.message)
    } finally {
      setEditLoading(false)
    }
  }

  async function handleDeletePurchase(purchaseId) {
    if (!confirm('Delete this purchase record? This cannot be undone.')) return
    try {
      await fetch(
        `${API_BASE}/purchases/${purchaseId}?user_id=${encodeURIComponent(userId)}`,
        { method: 'DELETE' }
      )
      setScreen('dashboard')
      setSelectedPurchase(null)
      loadPurchases()
      loadAlerts()
    } catch { /* silent */ }
  }

  async function handleAgentQuery() {
    if (!agentQuestion.trim()) return
    setAgentLoading(true)
    setAgentAnswer(null)
    try {
      const res = await fetch(`${API_BASE}/agent/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, question: agentQuestion }),
        signal: AbortSignal.timeout(30000),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setAgentAnswer(data.answer)
    } catch (err) {
      setAgentAnswer(`Error: ${err.message}`)
    } finally {
      setAgentLoading(false)
    }
  }

  function handleDisconnect() {
    localStorage.removeItem('wrd_user_id')
    localStorage.removeItem('wrd_user_email')
    setUserId('')
    setUserEmail('')
    setPurchases([])
    setAlerts([])
    setSelectedPurchase(null)
  }

  function openItemDetail(purchase) {
    setSelectedPurchase(purchase)
    setEditMode(false)
    setEditForm({})
    setEditError(null)
    setScreen('detail')
  }

  // ── Nav tabs ──────────────────────────────────────────────────────────────
  const navTabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '🏠' },
    { id: 'alerts', label: `Alerts${alerts.length > 0 ? ` (${alerts.length})` : ''}`, icon: '🔔' },
    { id: 'upload', label: 'Upload', icon: '📤' },
    { id: 'lookup', label: 'Quick Lookup', icon: '🔎' },
  ]

  // ── Screens ───────────────────────────────────────────────────────────────

  return (
    <>
      <div className="bg-orbs" aria-hidden="true" />
      <div className="app-shell">

        {/* Navbar */}
        <nav className="navbar fade-in">
          <div className="navbar-brand">
            <div className="navbar-logo-icon">🛡️</div>
            <span className="navbar-logo-text">Warranty Radar</span>
            <span className="version-pill">v0.3</span>
          </div>
          <div className="navbar-right">
            <StatusBadge status={healthStatus} />
            {isConnected && (
              <button className="btn btn-secondary" style={{ fontSize: '0.78rem', padding: '0.3rem 0.75rem' }}
                onClick={handleDisconnect}>Sign out</button>
            )}
          </div>
        </nav>

        {/* Tab nav (shown when connected) */}
        {isConnected && screen !== 'connect' && (
          <div className="tab-nav fade-in">
            {navTabs.map(tab => (
              <button
                key={tab.id}
                className={`tab-btn ${screen === tab.id || (screen === 'detail' && tab.id === 'dashboard') ? 'active' : ''}`}
                onClick={() => { setScreen(tab.id); if (tab.id === 'dashboard') loadPurchases(); }}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        )}

        {/* ── SCREEN: Connect Gmail ──────────────────────────────────────────── */}
        {screen === 'connect' && (
          <>
            <header className="hero fade-in">
              <div className="hero-eyebrow">🇮🇳 Designed for Indian Shoppers</div>
              <h1>
                Your <span className="gradient">warranty</span> and{' '}
                <span className="gradient">return window</span> tracker
              </h1>
              <p>
                Automatically reads your purchase confirmations, extracts warranty & return details,
                and keeps everything safe in one place.
              </p>
              <div className="hero-tags">
                <span className="hero-tag">📦 Amazon · Flipkart · Meesho</span>
                <span className="hero-tag">🛍️ Ajio · Myntra · Nykaa</span>
                <span className="hero-tag">⚡ Blinkit · Zepto · Swiggy</span>
                <span className="hero-tag">🌐 Hindi &amp; Hinglish supported</span>
              </div>
            </header>

            <section className="card card-glow fade-in">
              <div className="card-header">
                <div className="card-icon blue">📧</div>
                <div>
                  <div className="card-title">Connect Your Gmail</div>
                  <div className="card-subtitle">Grant read-only access to import your orders</div>
                </div>
              </div>
              <div className="privacy-row">
                <div className="privacy-item">
                  <span className="privacy-icon">🔒</span>
                  <span>Read-only — we never send, delete or modify your emails</span>
                </div>
                <div className="privacy-item">
                  <span className="privacy-icon">🗃️</span>
                  <span>Only purchase metadata is stored — email contents are never saved</span>
                </div>
                <div className="privacy-item">
                  <span className="privacy-icon">🔑</span>
                  <span>Revoke access at any time from your Google Account settings</span>
                </div>
              </div>
              <button id="btn-connect-gmail" className="btn btn-primary"
                style={{ marginTop: '1.25rem', width: 'fit-content' }}
                onClick={() => window.location.href = `${API_BASE}/auth/gmail/connect`}>
                <span>🔗</span> Connect with Google
              </button>
            </section>
          </>
        )}

        {/* ── SCREEN: Dashboard ──────────────────────────────────────────────── */}
        {screen === 'dashboard' && (
          <div className="screen-content fade-in">
            {/* Scan + user info bar */}
            <div className="dashboard-topbar">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <UserChip email={userEmail} />
                <span className="stat-chip">{purchases.length} items tracked</span>
                {alerts.length > 0 && (
                  <span className="stat-chip urgent" onClick={() => setScreen('alerts')} style={{ cursor: 'pointer' }}>
                    🔔 {alerts.length} upcoming alert{alerts.length !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <button id="btn-fetch-emails" className="btn btn-primary"
                onClick={handleFetchEmails} disabled={fetchLoading}>
                {fetchLoading
                  ? <><span className="spinner" /> Scanning inbox…</>
                  : '🔍 Scan Inbox'}
              </button>
            </div>

            {fetchError && <div className="notice error" style={{ marginBottom: '1rem' }}>Scan failed: {fetchError}</div>}
            {fetchResult && (
              <div className="notice success fade-in" style={{ marginBottom: '1rem' }}>
                Scanned {fetchResult.emails_scanned} emails · Saved {fetchResult.purchases_created} new records
                {fetchResult.purchases_failed > 0 && ` · ${fetchResult.purchases_failed} skipped`}
              </div>
            )}

            {purchasesLoading && (
              <div className="loading-row"><span className="spinner" /> Loading purchases…</div>
            )}
            {purchasesError && (
              <div className="notice error">Could not load purchases: {purchasesError}</div>
            )}

            {!purchasesLoading && purchases.length === 0 && (
              <div className="empty-state">
                <div className="empty-state-icon">📭</div>
                <div className="empty-state-title">No purchases tracked yet</div>
                <div className="empty-state-sub">Click "Scan Inbox" to import Gmail orders, or upload a document below.</div>
                <button className="btn btn-primary" onClick={() => setScreen('upload')}>Upload a Document</button>
              </div>
            )}

            <div className="purchase-grid">
              {purchases.map(p => (
                <PurchaseCard key={p.id} purchase={p} onSelect={openItemDetail} />
              ))}
            </div>
          </div>
        )}

        {/* ── SCREEN: Item Detail ────────────────────────────────────────────── */}
        {screen === 'detail' && selectedPurchase && (
          <div className="screen-content fade-in">
            <button className="back-btn" onClick={() => { setScreen('dashboard'); setEditMode(false); }}>
              ← Back to Dashboard
            </button>

            <div className="card card-glow">
              <div className="detail-header">
                <div>
                  <div className="detail-product">{fmt(selectedPurchase.product_name, 'Unnamed Product')}</div>
                  <div className="detail-sub">
                    {fmt(selectedPurchase.retailer || selectedPurchase.brand, 'Unknown Retailer')}
                    {selectedPurchase.purchase_date && ` · Purchased ${fmtDate(selectedPurchase.purchase_date)}`}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <ConfidenceBadge confidence={selectedPurchase.warranty_period?.confidence_score || 'low'} />
                  {selectedPurchase.warranty_period?.is_estimated && (
                    <span className="estimated-badge">Estimated</span>
                  )}
                </div>
              </div>

              {!editMode ? (
                <>
                  <div className="result-grid">
                    <ResultItem label="Product" value={fmt(selectedPurchase.product_name)} />
                    <ResultItem label="Brand" value={fmt(selectedPurchase.brand)} />
                    <ResultItem label="Retailer" value={fmt(selectedPurchase.retailer)} />
                    <ResultItem label="Purchase Date" value={fmtDate(selectedPurchase.purchase_date)} />
                    <ResultItem label="Price" value={fmtPrice(selectedPurchase.price)} className="accent" />
                    <ResultItem label="Source" value={selectedPurchase.source_type === 'email' ? '📧 Email' : '📄 Upload'} />
                    <ResultItem
                      label="Warranty Expires"
                      value={fmtDate(selectedPurchase.warranty_period?.warranty_end_date)}
                      urgencyDays={selectedPurchase.warranty_period?.warranty_end_date ? daysUntil(selectedPurchase.warranty_period.warranty_end_date) : null}
                    />
                    <ResultItem
                      label="Return Window Closes"
                      value={fmtDate(selectedPurchase.warranty_period?.return_window_end_date)}
                      urgencyDays={selectedPurchase.warranty_period?.return_window_end_date ? daysUntil(selectedPurchase.warranty_period.return_window_end_date) : null}
                    />
                    {selectedPurchase.family_member && (
                      <ResultItem label="Family Member" value={selectedPurchase.family_member} />
                    )}
                  </div>

                  {selectedPurchase.warranty_period?.source_snippet && (
                    <div className="source-snippet">
                      <div className="source-snippet-label">Extraction source</div>
                      <div className="source-snippet-text">{selectedPurchase.warranty_period.source_snippet}</div>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.25rem', flexWrap: 'wrap' }}>
                    <button className="btn btn-secondary"
                      onClick={() => { setEditMode(true); setEditForm({ ...selectedPurchase, warranty_end_date: selectedPurchase.warranty_period?.warranty_end_date || '', return_window_end_date: selectedPurchase.warranty_period?.return_window_end_date || '' }) }}>
                      ✏️ Edit Details
                    </button>
                    <button className="btn btn-danger"
                      onClick={() => handleDeletePurchase(selectedPurchase.id)}>
                      🗑 Delete
                    </button>
                  </div>
                </>
              ) : (
                /* Edit form */
                <div className="edit-form">
                  <div className="edit-grid">
                    <EditField label="Product Name" value={editForm.product_name || ''} onChange={v => setEditForm(f => ({ ...f, product_name: v }))} />
                    <EditField label="Brand" value={editForm.brand || ''} onChange={v => setEditForm(f => ({ ...f, brand: v }))} />
                    <EditField label="Retailer" value={editForm.retailer || ''} onChange={v => setEditForm(f => ({ ...f, retailer: v }))} />
                    <EditField label="Purchase Date" type="date" value={editForm.purchase_date || ''} onChange={v => setEditForm(f => ({ ...f, purchase_date: v }))} />
                    <EditField label="Price (₹)" type="number" value={editForm.price || ''} onChange={v => setEditForm(f => ({ ...f, price: v }))} />
                    <EditField label="Family Member" value={editForm.family_member || ''} onChange={v => setEditForm(f => ({ ...f, family_member: v }))} />
                    <EditField label="Warranty Expires" type="date" value={editForm.warranty_end_date || ''} onChange={v => setEditForm(f => ({ ...f, warranty_end_date: v }))} />
                    <EditField label="Return Window Closes" type="date" value={editForm.return_window_end_date || ''} onChange={v => setEditForm(f => ({ ...f, return_window_end_date: v }))} />
                  </div>
                  {editError && <div className="notice error" style={{ marginTop: '0.75rem' }}>{editError}</div>}
                  <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.25rem' }}>
                    <button className="btn btn-primary" onClick={handleSaveEdit} disabled={editLoading}>
                      {editLoading ? <><span className="spinner" /> Saving…</> : '💾 Save Changes'}
                    </button>
                    <button className="btn btn-secondary" onClick={() => { setEditMode(false); setEditError(null); }}>Cancel</button>
                  </div>
                </div>
              )}
            </div>

            {/* Agent chat for this item */}
            <div className="card" style={{ marginTop: '1rem' }}>
              <div className="card-header">
                <div className="card-icon violet">🤖</div>
                <div>
                  <div className="card-title">Ask the Warranty Agent</div>
                  <div className="card-subtitle">Natural-language questions about your purchases</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input id="agent-question-input" className="input" type="text" value={agentQuestion}
                  onChange={e => setAgentQuestion(e.target.value)}
                  placeholder={`Ask anything, e.g. "When does my ${selectedPurchase.product_name || 'product'} warranty expire?"`}
                  onKeyDown={e => e.key === 'Enter' && handleAgentQuery()}
                />
                <button className="btn btn-primary" onClick={handleAgentQuery} disabled={agentLoading || !agentQuestion.trim()}>
                  {agentLoading ? <span className="spinner" /> : '→'}
                </button>
              </div>
              {agentAnswer && (
                <div className="agent-answer fade-in">
                  <span className="agent-icon">🤖</span>
                  <p>{agentAnswer}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── SCREEN: Alerts ────────────────────────────────────────────────── */}
        {screen === 'alerts' && (
          <div className="screen-content fade-in">
            <div className="screen-header">
              <h2>🔔 Upcoming Alerts</h2>
              <button className="btn btn-secondary" onClick={loadAlerts}>Refresh</button>
            </div>

            {alertsLoading && <div className="loading-row"><span className="spinner" /> Loading alerts…</div>}

            {!alertsLoading && alerts.length === 0 && (
              <div className="empty-state">
                <div className="empty-state-icon">✅</div>
                <div className="empty-state-title">No upcoming alerts</div>
                <div className="empty-state-sub">All your products are in good standing for the next 60 days.</div>
              </div>
            )}

            <div className="alerts-list">
              {alerts.map(alert => {
                const cls = alert.is_overdue ? 'overdue' : urgencyColor(alert.days_until)
                return (
                  <div key={alert.alert_id} className={`alert-card ${cls}`}>
                    <div className="alert-card-left">
                      <AlertTypeIcon type={alert.alert_type} />
                    </div>
                    <div className="alert-card-body">
                      <div className="alert-product">{fmt(alert.product_name, 'Unknown Product')}</div>
                      <div className="alert-retailer">{fmt(alert.retailer || alert.brand)}</div>
                      <div className="alert-type-name">
                        <AlertTypeName type={alert.alert_type} />
                        {' · '}
                        {alert.is_overdue
                          ? <span className="overdue-text">Overdue by {Math.abs(alert.days_until)} days</span>
                          : alert.days_until === 0
                            ? <span>Due today</span>
                            : <span>Due in {alert.days_until} day{alert.days_until !== 1 ? 's' : ''} ({fmtDate(alert.fire_date)})</span>
                        }
                      </div>
                    </div>
                    <button className="btn btn-secondary" style={{ fontSize: '0.78rem', padding: '0.3rem 0.65rem' }}
                      onClick={() => {
                        const p = purchases.find(x => x.id === alert.purchase_id)
                        if (p) openItemDetail(p)
                      }}>
                      View
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* ── SCREEN: Upload ────────────────────────────────────────────────── */}
        {screen === 'upload' && (
          <div className="screen-content fade-in">
            <div className="screen-header">
              <h2>📤 Upload a Document</h2>
            </div>

            <div className="card">
              <div className="card-header">
                <div className="card-icon violet">📄</div>
                <div>
                  <div className="card-title">Invoice, Warranty Card, or Receipt</div>
                  <div className="card-subtitle">PDF, JPEG, PNG, WEBP, or TIFF · Max 20 MB</div>
                </div>
              </div>

              <div className={`file-zone ${dragover ? 'dragover' : ''}`}
                onDragOver={e => { e.preventDefault(); setDragover(true) }}
                onDragLeave={() => setDragover(false)}
                onDrop={e => { e.preventDefault(); setDragover(false); const f = e.dataTransfer.files?.[0]; if (f) setUploadFile(f) }}
                onClick={() => fileInputRef.current?.click()}>
                <input id="upload-file-input" ref={fileInputRef} type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.webp,.tiff"
                  onChange={e => setUploadFile(e.target.files?.[0])}
                  style={{ display: 'none' }} />
                <div className="file-zone-icon">{uploadFile ? '📎' : '☁️'}</div>
                {uploadFile
                  ? <div className="file-zone-selected">{uploadFile.name}</div>
                  : <div className="file-zone-text">Drag &amp; drop or <strong>click to browse</strong></div>
                }
              </div>

              <button id="btn-upload" className="btn btn-accent btn-full" style={{ marginTop: '0.75rem' }}
                onClick={handleUpload} disabled={!uploadFile || uploadLoading}>
                {uploadLoading ? <><span className="spinner" /> Processing document…</> : 'Analyse & Save'}
              </button>

              {uploadError && <div className="notice error" style={{ marginTop: '0.75rem' }}>{uploadError}</div>}
              {uploadResult && (
                <div className="fade-in" style={{ marginTop: '1rem' }}>
                  <div className="notice success">Purchase record saved.</div>
                  <ResultGrid result={uploadResult.extraction} ocrUsed={uploadResult.ocr_used} />
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── SCREEN: Quick Lookup ──────────────────────────────────────────── */}
        {screen === 'lookup' && (
          <div className="screen-content fade-in">
            <div className="screen-header">
              <h2>🔎 Quick Lookup</h2>
            </div>

            <div className="card">
              <div className="card-header">
                <div className="card-icon blue">🔎</div>
                <div>
                  <div className="card-title">Test Extraction</div>
                  <div className="card-subtitle">Paste order confirmation text to extract warranty details without saving</div>
                </div>
              </div>
              <textarea id="extraction-test-input" className="textarea" rows={6} value={testText}
                onChange={e => setTestText(e.target.value)}
                placeholder={`Paste your order confirmation here, e.g.:\n\nDear Customer,\nThank you for your order from Amazon.in\nOrder #405-9812345-0123456 placed on 15 August 2025.\n1 x Sony WH-1000XM5 Wireless Headphones (Black)\nOrder Total: ₹28,990.00 · 1-year manufacturer warranty.`}
                style={{ resize: 'vertical', minHeight: '140px', marginBottom: '0.75rem', fontFamily: 'monospace', fontSize: '0.82rem' }}
              />
              <button id="btn-test-extraction" className="btn btn-secondary btn-full"
                onClick={handleExtractionTest} disabled={!testText.trim() || testLoading}>
                {testLoading ? <><span className="spinner" /> Analysing…</> : 'Extract Warranty Details'}
              </button>
              {testError && <div className="notice error" style={{ marginTop: '0.75rem' }}>{testError}</div>}
              {testResult && (
                <div className="fade-in" style={{ marginTop: '1rem' }}>
                  <ResultGrid result={testResult} />
                </div>
              )}
            </div>

            {/* Agent chat (available from lookup when connected) */}
            {isConnected && (
              <div className="card" style={{ marginTop: '1rem' }}>
                <div className="card-header">
                  <div className="card-icon violet">🤖</div>
                  <div>
                    <div className="card-title">Ask the Warranty Agent</div>
                    <div className="card-subtitle">Ask anything about your purchase history</div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input id="agent-question-lookup" className="input" type="text" value={agentQuestion}
                    onChange={e => setAgentQuestion(e.target.value)}
                    placeholder="e.g. Which products can still be returned?"
                    onKeyDown={e => e.key === 'Enter' && handleAgentQuery()}
                  />
                  <button className="btn btn-primary" onClick={handleAgentQuery} disabled={agentLoading || !agentQuestion.trim()}>
                    {agentLoading ? <span className="spinner" /> : '→'}
                  </button>
                </div>
                {agentAnswer && (
                  <div className="agent-answer fade-in">
                    <span className="agent-icon">🤖</span>
                    <p>{agentAnswer}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <footer className="footer">
          <div className="footer-inner">
            <div className="footer-brand"><span>🛡️</span><span>Warranty Radar</span></div>
            <div className="footer-center">Protecting purchases across 10+ Indian retailers</div>
            <div className="footer-copy">© {new Date().getFullYear()} Warranty Radar · v0.3.0</div>
          </div>
        </footer>

      </div>
    </>
  )
}

// ── Shared display components ──────────────────────────────────────────────────

function ResultItem({ label, value, className = '', urgencyDays }) {
  const cls = urgencyDays !== null && urgencyDays !== undefined ? urgencyColor(urgencyDays) : ''
  return (
    <div className="result-item">
      <div className="result-item-label">{label}</div>
      <div className={`result-item-value ${className}`}>
        {value}
        {urgencyDays !== null && urgencyDays !== undefined && (
          <UrgencyChip days={urgencyDays} label={urgencyLabel(urgencyDays, label.split(' ')[0])} />
        )}
      </div>
    </div>
  )
}

function ResultGrid({ result, ocrUsed }) {
  return (
    <div className="fade-in">
      <div className="result-grid">
        <ResultItem label="Product Name" value={fmt(result.product_name)} />
        <ResultItem label="Brand" value={fmt(result.brand)} />
        <ResultItem label="Retailer" value={fmt(result.retailer)} />
        <ResultItem label="Purchase Date" value={fmtDate(result.purchase_date)} />
        <ResultItem label="Amount Paid" value={fmtPrice(result.price)} className="accent" />
        <ResultItem label="Warranty Period" value={result.warranty_period_months ? `${result.warranty_period_months} months` : '—'} />
        <ResultItem label="Return Window" value={result.return_window_days ? `${result.return_window_days} days` : '—'} />
        <div className="result-item">
          <div className="result-item-label">Accuracy</div>
          <div className="result-item-value">
            <ConfidenceBadge confidence={result.confidence} />
          </div>
        </div>
      </div>
      {ocrUsed && (
        <div className="ocr-badge">
          <span className="ocr-dot">📄</span>
          Document scanned with intelligent text recognition
        </div>
      )}
    </div>
  )
}

function EditField({ label, value, onChange, type = 'text' }) {
  return (
    <div className="edit-field">
      <label className="edit-field-label">{label}</label>
      <input className="input" type={type} value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={label}
      />
    </div>
  )
}
