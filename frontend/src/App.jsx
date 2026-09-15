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
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

// ── Components ─────────────────────────────────────────────────────────────────

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
  const labels = { high: 'High Accuracy', medium: 'Moderate Accuracy', low: 'Low Accuracy' }
  return (
    <span className={`confidence-badge ${confidence}`}>
      {labels[confidence] || confidence}
    </span>
  )
}

function ResultGrid({ result, ocrUsed }) {
  return (
    <div className="fade-in">
      <div className="result-grid">
        <ResultItem label="Product Name"   value={fmt(result.product_name)} />
        <ResultItem label="Brand"          value={fmt(result.brand)} />
        <ResultItem label="Retailer"       value={fmt(result.retailer)} />
        <ResultItem label="Purchase Date"  value={fmtDate(result.purchase_date)} />
        <ResultItem label="Amount Paid"    value={fmtPrice(result.price)} className="accent" />
        <ResultItem label="Warranty Period" value={result.warranty_period_months ? `${result.warranty_period_months} months` : '—'} />
        <ResultItem label="Return Window"  value={result.return_window_days ? `${result.return_window_days} days` : '—'} />
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

function ResultItem({ label, value, className = '' }) {
  return (
    <div className="result-item">
      <div className="result-item-label">{label}</div>
      <div className={`result-item-value ${className}`}>{value}</div>
    </div>
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

// ── Main App ───────────────────────────────────────────────────────────────────

export default function App() {
  const [healthStatus, setHealthStatus]   = useState('checking')
  const [healthData,   setHealthData]     = useState(null)
  const [userId,       setUserId]         = useState(() => localStorage.getItem('wrd_user_id') || '')
  const [userEmail,    setUserEmail]      = useState(() => localStorage.getItem('wrd_user_email') || '')

  const [uploadFile,    setUploadFile]    = useState(null)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadResult,  setUploadResult]  = useState(null)
  const [uploadError,   setUploadError]   = useState(null)
  const [dragover,      setDragover]      = useState(false)

  const [fetchLoading, setFetchLoading]   = useState(false)
  const [fetchResult,  setFetchResult]    = useState(null)
  const [fetchError,   setFetchError]     = useState(null)

  const [testText,    setTestText]        = useState('')
  const [testLoading, setTestLoading]     = useState(false)
  const [testResult,  setTestResult]      = useState(null)
  const [testError,   setTestError]       = useState(null)

  const fileInputRef = useRef(null)

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        setHealthData(data)
        setHealthStatus('ok')
      } catch {
        setHealthStatus('error')
      }
    }
    checkHealth()

    const params = new URLSearchParams(window.location.search)
    const callbackUserId = params.get('user_id')
    const callbackEmail  = params.get('email')
    if (callbackUserId && callbackEmail) {
      localStorage.setItem('wrd_user_id', callbackUserId)
      localStorage.setItem('wrd_user_email', callbackEmail)
      setUserId(callbackUserId)
      setUserEmail(callbackEmail)
      window.history.replaceState({}, '', '/')
    }
  }, [])

  function handleConnectGmail() {
    window.location.href = `${API_BASE}/auth/gmail/connect`
  }

  function handleFileSelect(file) {
    if (!file) return
    setUploadFile(file)
    setUploadResult(null)
    setUploadError(null)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragover(false)
    const file = e.dataTransfer.files?.[0]
    if (file) handleFileSelect(file)
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
        method: 'POST',
        body: formData,
        signal: AbortSignal.timeout(60000),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setUploadResult(data)
    } catch (err) {
      setUploadError(err.message)
    } finally {
      setUploadLoading(false)
    }
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
    } catch (err) {
      setFetchError(err.message)
    } finally {
      setFetchLoading(false)
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

  const isConnected = Boolean(userId && userEmail)

  return (
    <>
      <div className="bg-orbs" aria-hidden="true" />
      <div className="app-shell">

        {/* Navbar */}
        <nav className="navbar fade-in">
          <div className="navbar-brand">
            <div className="navbar-logo-icon">🛡️</div>
            <span className="navbar-logo-text">Warranty Radar</span>
          </div>
          <div className="navbar-right">
            <StatusBadge status={healthStatus} />
          </div>
        </nav>

        {/* Hero */}
        <header className="hero fade-in">
          <div className="hero-eyebrow">🇮🇳 Designed for Indian Shoppers</div>
          <h1>
            Your <span className="gradient">warranty</span> and{' '}
            <span className="gradient">return window</span> tracker
          </h1>
          <p>
            Warranty Radar automatically reads your purchase confirmations and invoices,
            extracts key warranty and return details, and keeps them in one place — so
            you are always protected.
          </p>
          <div className="hero-tags">
            <span className="hero-tag">📦 Amazon · Flipkart · Meesho</span>
            <span className="hero-tag">🛍️ Ajio · Myntra · Nykaa</span>
            <span className="hero-tag">⚡ Blinkit · Zepto · Swiggy Instamart</span>
            <span className="hero-tag">🌐 Hindi &amp; Hinglish supported</span>
          </div>
        </header>

        {/* Service Status */}
        {healthStatus !== 'ok' && (
          <section className="card card-glow fade-in" style={{ animationDelay: '50ms' }}>
            <div className="card-header">
              <div className="card-icon violet">📡</div>
              <div>
                <div className="card-title">Service Status</div>
                <div className="card-subtitle">Real-time platform availability</div>
              </div>
              <StatusBadge status={healthStatus} />
            </div>
            {healthStatus === 'error' && (
              <div className="notice error" style={{ marginTop: 0 }}>
                The service is currently unreachable. Please check your connection or try again shortly.
              </div>
            )}
          </section>
        )}

        {/* Gmail Connect */}
        <section className="card fade-in" style={{ animationDelay: '100ms' }}>
          <div className="card-header">
            <div className="card-icon blue">📧</div>
            <div>
              <div className="card-title">
                {isConnected ? 'Gmail Account' : 'Connect Your Gmail'}
              </div>
              <div className="card-subtitle">
                {isConnected
                  ? 'Your inbox is connected and ready to scan'
                  : 'Grant read-only access to automatically import order confirmations'}
              </div>
            </div>
          </div>

          {isConnected ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div className="notice success">
                Your Gmail account is connected. Orders and invoices will be identified automatically.
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <UserChip email={userEmail} />
                <button
                  id="btn-disconnect"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.8rem' }}
                  onClick={() => {
                    localStorage.removeItem('wrd_user_id')
                    localStorage.removeItem('wrd_user_email')
                    setUserId('')
                    setUserEmail('')
                  }}
                >
                  Remove Account
                </button>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="privacy-row">
                <div className="privacy-item">
                  <span className="privacy-icon">🔒</span>
                  <span>Read-only access — we never send, delete or modify your emails</span>
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
              <button
                id="btn-connect-gmail"
                className="btn btn-primary"
                style={{ width: 'fit-content' }}
                onClick={handleConnectGmail}
              >
                <span>🔗</span> Connect with Google
              </button>
            </div>
          )}
        </section>

        {/* Scan Inbox — only when connected */}
        {isConnected && (
          <section className="card fade-in" style={{ animationDelay: '150ms' }}>
            <div className="card-header">
              <div className="card-icon green">🔍</div>
              <div>
                <div className="card-title">Scan Inbox</div>
                <div className="card-subtitle">
                  Identify and import purchase records from your recent emails
                </div>
              </div>
            </div>
            <button
              id="btn-fetch-emails"
              className="btn btn-primary btn-full"
              onClick={handleFetchEmails}
              disabled={fetchLoading}
            >
              {fetchLoading
                ? <><span className="spinner" /> Scanning your inbox…</>
                : 'Scan for Purchases'}
            </button>
            {fetchError && (
              <div className="notice error" style={{ marginTop: '0.75rem' }}>
                Unable to complete the scan. {fetchError}
              </div>
            )}
            {fetchResult && (
              <div className="fade-in">
                <div className="summary-row">
                  <div className="summary-stat">
                    <div className="summary-stat-number" style={{ color: 'var(--clr-accent)' }}>
                      {fetchResult.emails_scanned}
                    </div>
                    <div className="summary-stat-label">Emails reviewed</div>
                  </div>
                  <div className="summary-stat">
                    <div className="summary-stat-number" style={{ color: 'var(--clr-success)' }}>
                      {fetchResult.purchases_created}
                    </div>
                    <div className="summary-stat-label">Records saved</div>
                  </div>
                  <div className="summary-stat">
                    <div className="summary-stat-number" style={{ color: 'var(--clr-danger)' }}>
                      {fetchResult.purchases_failed}
                    </div>
                    <div className="summary-stat-label">Not processed</div>
                  </div>
                </div>
                {fetchResult.errors?.length > 0 && (
                  <div className="error-list">
                    {fetchResult.errors.map((e, i) => <p key={i}>{e}</p>)}
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {/* Upload Document */}
        <section className="card fade-in" style={{ animationDelay: '200ms' }}>
          <div className="card-header">
            <div className="card-icon violet">📄</div>
            <div>
              <div className="card-title">Upload a Document</div>
              <div className="card-subtitle">
                Submit an invoice, warranty card, or purchase receipt for extraction
              </div>
            </div>
          </div>

          {!isConnected && (
            <div className="notice info" style={{ marginBottom: '1rem' }}>
              Please connect your Gmail account before uploading documents.
            </div>
          )}

          <div
            className={`file-zone ${dragover ? 'dragover' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragover(true) }}
            onDragLeave={() => setDragover(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              id="upload-file-input"
              ref={fileInputRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.webp,.tiff"
              onChange={e => handleFileSelect(e.target.files?.[0])}
              style={{ display: 'none' }}
            />
            <div className="file-zone-icon">
              {uploadFile ? '📎' : '☁️'}
            </div>
            {uploadFile ? (
              <div className="file-zone-selected">{uploadFile.name}</div>
            ) : (
              <div className="file-zone-text">
                Drag &amp; drop a PDF or image, or <strong>click to browse</strong>
                <div className="file-zone-hint">Supports PDF, JPEG, PNG, WEBP, TIFF · Max 20 MB</div>
              </div>
            )}
          </div>

          <button
            id="btn-upload"
            className="btn btn-accent btn-full"
            style={{ marginTop: '0.75rem' }}
            onClick={handleUpload}
            disabled={!uploadFile || !isConnected || uploadLoading}
          >
            {uploadLoading ? <><span className="spinner" /> Processing document…</> : 'Analyse &amp; Save'}
          </button>

          {uploadError && (
            <div className="notice error" style={{ marginTop: '0.75rem' }}>
              Document could not be processed. {uploadError}
            </div>
          )}
          {uploadResult && (
            <div className="fade-in" style={{ marginTop: '1rem' }}>
              <div className="notice success">
                Purchase record saved successfully.
              </div>
              <ResultGrid result={uploadResult.extraction} ocrUsed={uploadResult.ocr_used} />
            </div>
          )}
        </section>

        {/* Quick Lookup */}
        <section className="card fade-in" style={{ animationDelay: '250ms' }}>
          <div className="card-header">
            <div className="card-icon blue">🔎</div>
            <div>
              <div className="card-title">Quick Lookup</div>
              <div className="card-subtitle">
                Paste the text from an order confirmation email or invoice to extract warranty details
              </div>
            </div>
          </div>
          <textarea
            id="extraction-test-input"
            className="textarea"
            rows={6}
            value={testText}
            onChange={e => setTestText(e.target.value)}
            placeholder={`Paste your order confirmation text here, for example:

Dear Customer,
Thank you for your order from Amazon.in
Order #405-9812345-0123456 placed on 15 August 2025.
1 x Sony WH-1000XM5 Wireless Headphones (Black)
Order Total: ₹28,990.00
1-year manufacturer's warranty included.`}
            style={{ resize: 'vertical', minHeight: '140px', marginBottom: '0.75rem', fontFamily: 'monospace', fontSize: '0.82rem' }}
          />
          <button
            id="btn-test-extraction"
            className="btn btn-secondary btn-full"
            onClick={handleExtractionTest}
            disabled={!testText.trim() || testLoading}
          >
            {testLoading ? <><span className="spinner" /> Analysing…</> : 'Extract Warranty Details'}
          </button>
          {testError && (
            <div className="notice error" style={{ marginTop: '0.75rem' }}>
              Extraction could not be completed. {testError}
            </div>
          )}
          {testResult && (
            <div className="fade-in" style={{ marginTop: '1rem' }}>
              <ResultGrid result={testResult} />
            </div>
          )}
        </section>

        <footer className="footer">
          <div className="footer-inner">
            <div className="footer-brand">
              <span>🛡️</span>
              <span>Warranty Radar</span>
            </div>
            <div className="footer-center">
              Protecting your purchases across 10+ Indian retailers
            </div>
            <div className="footer-copy">© {new Date().getFullYear()} Warranty Radar. All rights reserved.</div>
          </div>
        </footer>

      </div>
    </>
  )
}
