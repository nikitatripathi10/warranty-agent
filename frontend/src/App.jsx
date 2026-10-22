import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import './index.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr + 'T00:00:00')
  return Math.round((target - today) / 86400000)
}
function urgencyColor(days) {
  if (days === null) return ''
  if (days < 0)  return 'overdue'
  if (days <= 7) return 'critical'
  if (days <= 30) return 'warning'
  return 'safe'
}
function urgencyLabel(days, type) {
  if (days === null) return null
  if (days < 0) return `${type} expired ${Math.abs(days)}d ago`
  if (days === 0) return `${type} expires today!`
  if (days === 1) return `${type} expires tomorrow`
  return `${type} in ${days}d`
}

// ── Theme Hook ─────────────────────────────────────────────────────────────────
function useTheme() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('wrd_theme') || 'dark'
  })
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('wrd_theme', theme)
  }, [theme])
  const toggle = () => setTheme(t => t === 'dark' ? 'light' : 'dark')
  return [theme, toggle]
}

// ── Toast Hook ─────────────────────────────────────────────────────────────────
let toastId = 0
function useToasts() {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++toastId
    setToasts(t => [...t, { id, message, type }])
    setTimeout(() => {
      setToasts(t => t.map(x => x.id === id ? { ...x, exit: true } : x))
      setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 350)
    }, duration)
    return id
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(t => t.map(x => x.id === id ? { ...x, exit: true } : x))
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 350)
  }, [])

  return [toasts, addToast, removeToast]
}

// ── URL Search Params Hook ─────────────────────────────────────────────────────
function useURLParams() {
  const getParams = useCallback(() => new URLSearchParams(window.location.search), [])

  const setParam = useCallback((key, value) => {
    const params = getParams()
    if (value) params.set(key, value)
    else params.delete(key)
    const str = params.toString()
    window.history.replaceState({}, '', str ? `?${str}` : window.location.pathname)
  }, [getParams])

  const getParam = useCallback((key, def = '') => getParams().get(key) || def, [getParams])

  return { setParam, getParam }
}

// ── Small Components ───────────────────────────────────────────────────────────
function StatusBadge({ status }) {
  if (status === 'checking') return (
    <span className="status-pill loading">
      <span className="spinner" style={{ width: 10, height: 10, borderWidth: 1.5 }} />
      Connecting…
    </span>
  )
  if (status === 'ok') return (
    <span className="status-pill ok"><span className="status-dot" />All Systems Operational</span>
  )
  return <span className="status-pill error"><span className="status-dot" />Service Unavailable</span>
}

function ConfidenceBadge({ confidence }) {
  const labels = { high: 'High', medium: 'Moderate', low: 'Low' }
  return <span className={`confidence-badge ${confidence}`}>{labels[confidence] || confidence}</span>
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
  const icons = { return_window_expiry: '🔄', warranty_expiry: '🛡️', recall: '⚠️' }
  return <span>{icons[type] || '🔔'}</span>
}

function AlertTypeName({ type }) {
  const names = { return_window_expiry: 'Return Window', warranty_expiry: 'Warranty Expiry', recall: 'Product Recall' }
  return <>{names[type] || type}</>
}

// ── Skeleton Loader ────────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <div className="skeleton skeleton-avatar" style={{ width: 28, height: 28, flexShrink: 0 }} />
        <div className="skeleton skeleton-text" style={{ flex: 1 }} />
        <div className="skeleton skeleton-text" style={{ width: 60 }} />
      </div>
      <div className="skeleton skeleton-title" style={{ width: '75%' }} />
      <div className="skeleton skeleton-text" style={{ width: '50%' }} />
      <div style={{ display: 'flex', gap: '0.4rem' }}>
        <div className="skeleton skeleton-text" style={{ width: 80 }} />
        <div className="skeleton skeleton-text" style={{ width: 90 }} />
      </div>
    </div>
  )
}

function SkeletonGrid() {
  return (
    <div className="purchase-grid">
      {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
    </div>
  )
}

function SkeletonStats() {
  return (
    <div className="stats-grid">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="stat-card">
          <div className="skeleton skeleton-text" style={{ width: 90, marginBottom: '0.5rem' }} />
          <div className="skeleton skeleton-title" style={{ width: 60, height: '1.6rem', marginBottom: '0.3rem' }} />
          <div className="skeleton skeleton-text" style={{ width: 70 }} />
        </div>
      ))}
    </div>
  )
}

// ── Toast Stack ────────────────────────────────────────────────────────────────
function ToastStack({ toasts, onRemove }) {
  return (
    <div className="toast-stack">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.type}${t.exit ? ' exit' : ''}`}>
          <span>{t.type === 'success' ? '✅' : t.type === 'error' ? '❌' : 'ℹ️'}</span>
          <span>{t.message}</span>
          <button className="toast-close" onClick={() => onRemove(t.id)} aria-label="Dismiss">×</button>
        </div>
      ))}
    </div>
  )
}

// ── Onboarding Steps ───────────────────────────────────────────────────────────
function OnboardingSteps({ step }) {
  const steps = [
    { label: 'Connect Gmail' },
    { label: 'Scan Orders' },
    { label: 'Review Items' },
  ]
  return (
    <div className="onboarding-steps">
      {steps.map((s, i) => {
        const isCompleted = i < step
        const isActive = i === step
        return (
          <div
            key={i}
            className={`onboarding-step ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''}`}
          >
            <div className="onboarding-step-circle">
              {isCompleted ? '✓' : i + 1}
            </div>
            <div className="onboarding-step-label">{s.label}</div>
          </div>
        )
      })}
    </div>
  )
}

// ── Warranty Timeline ──────────────────────────────────────────────────────────
function WarrantyTimeline({ purchases, onSelect }) {
  const today = new Date(); today.setHours(0, 0, 0, 0)

  // Build items with warranty end dates
  const items = purchases.flatMap(p => {
    const wp = p.warranty_period
    const arr = []
    if (wp?.warranty_end_date) {
      arr.push({ purchase: p, date: wp.warranty_end_date, label: p.product_name || 'Product', type: 'warranty' })
    }
    if (wp?.return_window_end_date) {
      arr.push({ purchase: p, date: wp.return_window_end_date, label: p.product_name || 'Product', type: 'return' })
    }
    return arr
  }).filter(x => x.date)

  if (items.length === 0) return null

  // Get date range (today ± 180 days)
  const windowDays = 180
  const startDate = new Date(today)
  startDate.setDate(startDate.getDate() - 30)
  const endDate = new Date(today)
  endDate.setDate(endDate.getDate() + windowDays)
  const totalRange = endDate - startDate

  const todayPct = ((today - startDate) / totalRange) * 100

  return (
    <div className="timeline-section fade-in">
      <div className="timeline-header">
        <h3>📅 Warranty Timeline</h3>
        <span style={{ fontSize: '0.72rem', color: 'var(--clr-text-muted)' }}>
          Next 6 months
        </span>
      </div>
      <div className="timeline-track">
        {/* Today marker */}
        <div className="timeline-today" style={{ left: `${todayPct}%` }} />

        {items.map((item, i) => {
          const itemDate = new Date(item.date + 'T00:00:00')
          const pct = ((itemDate - startDate) / totalRange) * 100
          if (pct < 0 || pct > 100) return null
          const days = daysUntil(item.date)
          const cls = urgencyColor(days)
          return (
            <div
              key={i}
              className={`timeline-item ${cls}`}
              style={{ left: `${Math.max(0, Math.min(96, pct))}%`, width: `${Math.max(3, Math.min(12, 100 - pct))}%` }}
              title={`${item.label} — ${item.type === 'warranty' ? 'Warranty' : 'Return'} ends ${fmtDate(item.date)}`}
              onClick={() => onSelect(item.purchase)}
            >
              {pct < 88 && item.label.split(' ')[0]}
            </div>
          )
        })}
      </div>
      <div className="timeline-legend">
        <div className="timeline-legend-item"><div className="legend-dot safe" />Safe (&gt;30d)</div>
        <div className="timeline-legend-item"><div className="legend-dot warning" />Expiring (&lt;30d)</div>
        <div className="timeline-legend-item"><div className="legend-dot critical" />Critical (&lt;7d)</div>
        <div className="timeline-legend-item" style={{ marginLeft: 'auto', fontStyle: 'italic' }}>
          Click a bar to view details
        </div>
      </div>
    </div>
  )
}

// ── Summary Stats Cards ────────────────────────────────────────────────────────
function SummaryStats({ purchases, alerts, onAlerts }) {
  const totalValue = purchases.reduce((acc, p) => acc + (Number(p.price) || 0), 0)
  const expiringSoon = purchases.filter(p => {
    const d = p.warranty_period?.warranty_end_date
    if (!d) return false
    const days = daysUntil(d)
    return days !== null && days >= 0 && days <= 30
  }).length
  const activeAlerts = alerts.length

  return (
    <div className="stats-grid">
      <div className="stat-card">
        <div className="stat-card-label">📦 Total Tracked</div>
        <div className="stat-card-value primary">{purchases.length}</div>
        <div className="stat-card-sub">purchases</div>
      </div>
      <div className="stat-card clickable" onClick={onAlerts} title="View alerts">
        <div className="stat-card-label">⏰ Expiring Soon</div>
        <div className={`stat-card-value ${expiringSoon > 0 ? 'warning' : 'success'}`}>{expiringSoon}</div>
        <div className="stat-card-sub">in next 30 days</div>
      </div>
      <div className="stat-card clickable" onClick={onAlerts} title="View all alerts">
        <div className="stat-card-label">🔔 Active Alerts</div>
        <div className={`stat-card-value ${activeAlerts > 0 ? 'danger' : 'success'}`}>{activeAlerts}</div>
        <div className="stat-card-sub">need attention</div>
      </div>
      <div className="stat-card">
        <div className="stat-card-label">💰 Value Protected</div>
        <div className="stat-card-value primary" style={{ fontSize: '1.35rem' }}>
          {totalValue > 0 ? `₹${(totalValue / 1000).toFixed(1)}K` : '—'}
        </div>
        <div className="stat-card-sub">total purchases</div>
      </div>
    </div>
  )
}

// ── Purchase Card ──────────────────────────────────────────────────────────────
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
        <div className="purchase-card-icon">{purchase.source_type === 'email' ? '📧' : '📄'}</div>
        <div className="purchase-card-retailer">{fmt(purchase.retailer || purchase.brand, 'Unknown')}</div>
        <ConfidenceBadge confidence={wp?.confidence_score || 'low'} />
      </div>
      <div className="purchase-card-product">{fmt(purchase.product_name, 'Unnamed Product')}</div>
      <div className="purchase-card-meta">
        <span>🗓 {fmtDate(purchase.purchase_date)}</span>
        {purchase.price && <span>💰 {fmtPrice(purchase.price)}</span>}
      </div>
      {mostUrgent !== null && (
        <div className="purchase-card-urgency">
          {returnDays !== null && <UrgencyChip days={returnDays} label={urgencyLabel(returnDays, 'Return')} />}
          {warrantyDays !== null && <UrgencyChip days={warrantyDays} label={urgencyLabel(warrantyDays, 'Warranty')} />}
          {wp?.is_estimated && <span className="estimated-badge">Estimated</span>}
        </div>
      )}
    </div>
  )
}

// ── Purchase List Item ─────────────────────────────────────────────────────────
function PurchaseListItem({ purchase, onSelect }) {
  const wp = purchase.warranty_period
  const returnDays = wp?.return_window_end_date ? daysUntil(wp.return_window_end_date) : null
  const warrantyDays = wp?.warranty_end_date ? daysUntil(wp.warranty_end_date) : null
  const urgentDays = [returnDays, warrantyDays].filter(d => d !== null)
  const mostUrgent = urgentDays.length > 0 ? Math.min(...urgentDays) : null
  const cls = mostUrgent !== null ? urgencyColor(mostUrgent) : ''

  return (
    <div className={`purchase-list-item ${cls}`} onClick={() => onSelect(purchase)} role="button" tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onSelect(purchase)}>
      <div className="list-item-icon">{purchase.source_type === 'email' ? '📧' : '📄'}</div>
      <div className="list-item-main">
        <div className="list-item-product">{fmt(purchase.product_name, 'Unnamed Product')}</div>
        <div className="list-item-sub">
          <span>{fmt(purchase.retailer || purchase.brand, 'Unknown')}</span>
          {purchase.purchase_date && <span>🗓 {fmtDate(purchase.purchase_date)}</span>}
          {purchase.price && <span>💰 {fmtPrice(purchase.price)}</span>}
        </div>
      </div>
      <div className="list-item-right">
        {warrantyDays !== null && <UrgencyChip days={warrantyDays} label={urgencyLabel(warrantyDays, 'Warranty')} />}
        <ConfidenceBadge confidence={wp?.confidence_score || 'low'} />
      </div>
    </div>
  )
}

// ── Shared Display Components ──────────────────────────────────────────────────
function ResultItem({ label, value, className = '', urgencyDays }) {
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
          <span>📄</span> Document scanned with intelligent text recognition
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
        onChange={e => onChange(e.target.value)} placeholder={label} />
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN APP
// ══════════════════════════════════════════════════════════════════════════════
export default function App() {
  // ── Auth state ──────────────────────────────────────────────────────────────
  const [userId, setUserId] = useState(() => localStorage.getItem('wrd_user_id') || '')
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem('wrd_user_email') || '')
  const isConnected = Boolean(userId && userEmail)

  // ── Theme ───────────────────────────────────────────────────────────────────
  const [theme, toggleTheme] = useTheme()

  // ── Toasts ──────────────────────────────────────────────────────────────────
  const [toasts, addToast, removeToast] = useToasts()

  // ── Navigation ──────────────────────────────────────────────────────────────
  const [screen, setScreen] = useState('connect')

  // ── Onboarding step (0=connect, 1=scan, 2=review) ───────────────────────────
  const [onboardStep, setOnboardStep] = useState(0)
  const [hasOnboarded, setHasOnboarded] = useState(() =>
    Boolean(localStorage.getItem('wrd_onboarded'))
  )

  // ── Health ──────────────────────────────────────────────────────────────────
  const [healthStatus, setHealthStatus] = useState('checking')

  // ── Purchases ───────────────────────────────────────────────────────────────
  const [purchases, setPurchases] = useState([])
  const [purchasesLoading, setPurchasesLoading] = useState(false)
  const [purchasesError, setPurchasesError] = useState(null)
  const [selectedPurchase, setSelectedPurchase] = useState(null)

  // ── Edit modal ──────────────────────────────────────────────────────────────
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState({})
  const [editLoading, setEditLoading] = useState(false)
  const [editError, setEditError] = useState(null)

  // ── Alerts ──────────────────────────────────────────────────────────────────
  const [alerts, setAlerts] = useState([])
  const [alertsLoading, setAlertsLoading] = useState(false)

  // ── Upload ──────────────────────────────────────────────────────────────────
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadResult, setUploadResult] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const [dragover, setDragover] = useState(false)

  // ── Fetch emails ─────────────────────────────────────────────────────────────
  const [fetchLoading, setFetchLoading] = useState(false)
  const [fetchResult, setFetchResult] = useState(null)
  const [fetchError, setFetchError] = useState(null)

  // ── Quick lookup ─────────────────────────────────────────────────────────────
  const [testText, setTestText] = useState('')
  const [testLoading, setTestLoading] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testError, setTestError] = useState(null)

  // ── Agent chat ───────────────────────────────────────────────────────────────
  const [agentQuestion, setAgentQuestion] = useState('')
  const [agentAnswer, setAgentAnswer] = useState(null)
  const [agentLoading, setAgentLoading] = useState(false)

  // ── View / filters ───────────────────────────────────────────────────────────
  const { setParam, getParam } = useURLParams()
  const [viewMode, setViewMode] = useState(() => localStorage.getItem('wrd_view') || 'card')
  const [searchQ, setSearchQ] = useState(() => getParam('q'))
  const [filterBrand, setFilterBrand] = useState(() => getParam('brand'))
  const [filterStatus, setFilterStatus] = useState(() => getParam('status'))
  const [filterConf, setFilterConf] = useState(() => getParam('conf'))
  const [sortBy, setSortBy] = useState(() => getParam('sort') || 'date_desc')

  const fileInputRef = useRef(null)

  // ── URL sync ──────────────────────────────────────────────────────────────────
  useEffect(() => { setParam('q', searchQ) }, [searchQ, setParam])
  useEffect(() => { setParam('brand', filterBrand) }, [filterBrand, setParam])
  useEffect(() => { setParam('status', filterStatus) }, [filterStatus, setParam])
  useEffect(() => { setParam('conf', filterConf) }, [filterConf, setParam])
  useEffect(() => { setParam('sort', sortBy !== 'date_desc' ? sortBy : '') }, [sortBy, setParam])
  useEffect(() => { localStorage.setItem('wrd_view', viewMode) }, [viewMode])

  // ── Boot ──────────────────────────────────────────────────────────────────────
  useEffect(() => {
    // Handle OAuth callback
    const params = new URLSearchParams(window.location.search)
    const cbUserId = params.get('user_id')
    const cbEmail = params.get('email')
    if (cbUserId && cbEmail) {
      localStorage.setItem('wrd_user_id', cbUserId)
      localStorage.setItem('wrd_user_email', cbEmail)
      setUserId(cbUserId)
      setUserEmail(cbEmail)
      window.history.replaceState({}, '', '/')
      // Move onboarding to step 1 (scan)
      setOnboardStep(1)
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
      if (!hasOnboarded) setOnboardStep(1)
    } else {
      setScreen('connect')
    }
  }, [isConnected]) // eslint-disable-line

  // ── API calls ─────────────────────────────────────────────────────────────────
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
      addToast(`Scanned ${data.emails_scanned} emails · ${data.purchases_created} new records saved`, 'success')
      loadPurchases()
      loadAlerts()
      // Advance onboarding
      if (onboardStep === 1) setOnboardStep(2)
    } catch (err) {
      setFetchError(err.message)
      addToast(`Scan failed: ${err.message}`, 'error')
    } finally {
      setFetchLoading(false)
    }
  }

  async function handleUpload() {
    if (!uploadFile || !userId) return
    setUploadLoading(true)
    setUploadResult(null)
    setUploadError(null)
    setUploadProgress(10)
    const formData = new FormData()
    formData.append('file', uploadFile)
    formData.append('user_id', userId)
    try {
      // Simulate progress
      const prog = setInterval(() => setUploadProgress(p => Math.min(p + 12, 85)), 600)
      const res = await fetch(`${API_BASE}/ingestion/upload`, {
        method: 'POST', body: formData, signal: AbortSignal.timeout(60000),
      })
      clearInterval(prog)
      setUploadProgress(100)
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setUploadResult(data)
      addToast('Document processed and saved!', 'success')
      loadPurchases()
      loadAlerts()
    } catch (err) {
      setUploadError(err.message)
      addToast(`Upload failed: ${err.message}`, 'error')
    } finally {
      setUploadLoading(false)
      setTimeout(() => setUploadProgress(0), 1000)
    }
  }

  async function handleExtractionTest() {
    if (!testText.trim()) return
    setTestLoading(true)
    setTestResult(null)
    setTestError(null)
    try {
      const res = await fetch(`${API_BASE}/extraction/test`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: testText }), signal: AbortSignal.timeout(45000),
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
        { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
      )
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setSelectedPurchase(data)
      setEditMode(false)
      addToast('Purchase record updated!', 'success')
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
      addToast('Purchase record deleted.', 'info')
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
        method: 'POST', headers: { 'Content-Type': 'application/json' },
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
    setUserId(''); setUserEmail('')
    setPurchases([]); setAlerts([])
    setSelectedPurchase(null)
  }

  function openItemDetail(purchase) {
    setSelectedPurchase(purchase)
    setEditMode(false); setEditForm({}); setEditError(null)
    setScreen('detail')
  }

  function completeOnboarding() {
    localStorage.setItem('wrd_onboarded', '1')
    setHasOnboarded(true)
    setOnboardStep(3)
  }

  // ── Filtered + sorted purchases ─────────────────────────────────────────────
  const uniqueBrands = useMemo(() => {
    const s = new Set(purchases.map(p => p.retailer || p.brand).filter(Boolean))
    return [...s].sort()
  }, [purchases])

  const filteredPurchases = useMemo(() => {
    let list = [...purchases]

    // Search
    if (searchQ) {
      const q = searchQ.toLowerCase()
      list = list.filter(p =>
        (p.product_name || '').toLowerCase().includes(q) ||
        (p.retailer || '').toLowerCase().includes(q) ||
        (p.brand || '').toLowerCase().includes(q)
      )
    }
    // Brand filter
    if (filterBrand) {
      list = list.filter(p => (p.retailer || p.brand || '') === filterBrand)
    }
    // Confidence filter
    if (filterConf) {
      list = list.filter(p => (p.warranty_period?.confidence_score || 'low') === filterConf)
    }
    // Status filter
    if (filterStatus === 'expiring') {
      list = list.filter(p => {
        const d = p.warranty_period?.warranty_end_date
        if (!d) return false
        const days = daysUntil(d)
        return days !== null && days >= 0 && days <= 30
      })
    } else if (filterStatus === 'overdue') {
      list = list.filter(p => {
        const d = p.warranty_period?.warranty_end_date
        if (!d) return false
        return daysUntil(d) < 0
      })
    } else if (filterStatus === 'safe') {
      list = list.filter(p => {
        const d = p.warranty_period?.warranty_end_date
        if (!d) return true
        const days = daysUntil(d)
        return days !== null && days > 30
      })
    }

    // Sort
    if (sortBy === 'date_asc') {
      list.sort((a, b) => (a.purchase_date || '').localeCompare(b.purchase_date || ''))
    } else if (sortBy === 'date_desc') {
      list.sort((a, b) => (b.purchase_date || '').localeCompare(a.purchase_date || ''))
    } else if (sortBy === 'warranty_asc') {
      list.sort((a, b) => {
        const da = a.warranty_period?.warranty_end_date || '9999-12-31'
        const db = b.warranty_period?.warranty_end_date || '9999-12-31'
        return da.localeCompare(db)
      })
    } else if (sortBy === 'price_desc') {
      list.sort((a, b) => (Number(b.price) || 0) - (Number(a.price) || 0))
    } else if (sortBy === 'name_asc') {
      list.sort((a, b) => (a.product_name || '').localeCompare(b.product_name || ''))
    }

    return list
  }, [purchases, searchQ, filterBrand, filterConf, filterStatus, sortBy])

  const hasActiveFilters = searchQ || filterBrand || filterStatus || filterConf || sortBy !== 'date_desc'

  function clearFilters() {
    setSearchQ(''); setFilterBrand(''); setFilterStatus(''); setFilterConf('')
    setSortBy('date_desc')
  }

  // ── Nav tabs ─────────────────────────────────────────────────────────────────
  const navTabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '🏠' },
    { id: 'alerts', label: `Alerts${alerts.length > 0 ? ` (${alerts.length})` : ''}`, icon: '🔔' },
    { id: 'upload', label: 'Upload', icon: '📤' },
    { id: 'lookup', label: 'Quick Lookup', icon: '🔎' },
  ]

  // ── Low confidence items (for onboarding step 2) ──────────────────────────
  const lowConfPurchases = purchases.filter(
    p => (p.warranty_period?.confidence_score || 'low') === 'low'
  )

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════════
  return (
    <>
      <div className="bg-orbs" aria-hidden="true" />

      {/* Toast stack */}
      <ToastStack toasts={toasts} onRemove={removeToast} />

      <div className="app-shell">

        {/* ── Navbar ── */}
        <nav className="navbar fade-in">
          <div className="navbar-brand">
            <div className="navbar-logo-icon">🛡️</div>
            <span className="navbar-logo-text">Warranty Radar</span>
            <span className="version-pill">v0.4</span>
          </div>
          <div className="navbar-right">
            <StatusBadge status={healthStatus} />
            <button
              id="btn-theme-toggle"
              className="theme-toggle"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
            {isConnected && (
              <button className="btn btn-secondary btn-sm" onClick={handleDisconnect}>
                Sign out
              </button>
            )}
          </div>
        </nav>

        {/* ── Tab nav ── */}
        {isConnected && screen !== 'connect' && (
          <div className="tab-nav fade-in">
            {navTabs.map(tab => (
              <button key={tab.id}
                className={`tab-btn ${screen === tab.id || (screen === 'detail' && tab.id === 'dashboard') ? 'active' : ''}`}
                onClick={() => { setScreen(tab.id); if (tab.id === 'dashboard') loadPurchases() }}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        )}

        {/* ════════════════════════════════════════════════════
            SCREEN: Connect Gmail (Onboarding)
            ════════════════════════════════════════════════════ */}
        {screen === 'connect' && (
          <>
            <header className="hero fade-in">
              <div className="hero-eyebrow">🇮🇳 Designed for Indian Shoppers</div>
              <h1>
                Your <span className="gradient">warranty</span> and{' '}
                <span className="gradient">return window</span> tracker
              </h1>
              <p>
                Automatically reads your purchase confirmations, extracts warranty &amp; return details,
                and keeps everything safe in one place.
              </p>
              <div className="hero-tags">
                <span className="hero-tag">📦 Amazon · Flipkart · Meesho</span>
                <span className="hero-tag">🛍️ Ajio · Myntra · Nykaa</span>
                <span className="hero-tag">⚡ Blinkit · Zepto · Swiggy</span>
                <span className="hero-tag">🌐 Hindi &amp; Hinglish supported</span>
              </div>
            </header>

            {/* 3-step onboarding progress */}
            <OnboardingSteps step={onboardStep} />

            <section className="card card-glow fade-in">
              <div className="card-header">
                <div className="card-icon blue">📧</div>
                <div>
                  <div className="card-title">
                    {onboardStep === 0 ? 'Step 1: Connect Your Gmail' : 'Connect Your Gmail'}
                  </div>
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
              <button
                id="btn-connect-gmail"
                className="btn btn-primary"
                style={{ marginTop: '1.25rem', width: 'fit-content' }}
                onClick={() => window.location.href = `${API_BASE}/auth/gmail/connect`}
              >
                <span>🔗</span> Connect with Google
              </button>
            </section>
          </>
        )}

        {/* ════════════════════════════════════════════════════
            SCREEN: Dashboard
            ════════════════════════════════════════════════════ */}
        {screen === 'dashboard' && (
          <div className="screen-content fade-in">

            {/* Onboarding banner (steps 1 & 2) */}
            {!hasOnboarded && onboardStep < 3 && (
              <div className="card card-glow" style={{ marginBottom: '1rem', padding: '1.25rem 1.5rem' }}>
                <OnboardingSteps step={onboardStep} />
                {onboardStep === 1 && (
                  <div style={{ textAlign: 'center' }}>
                    <p style={{ color: 'var(--clr-text-secondary)', fontSize: '0.88rem', marginBottom: '0.85rem' }}>
                      🎉 Gmail connected! Now scan your inbox to import purchase orders.
                    </p>
                    <button className="btn btn-primary" onClick={handleFetchEmails} disabled={fetchLoading}>
                      {fetchLoading ? <><span className="spinner" /> Scanning…</> : '🔍 Scan Inbox Now'}
                    </button>
                  </div>
                )}
                {onboardStep === 2 && (
                  <div style={{ textAlign: 'center' }}>
                    <p style={{ color: 'var(--clr-text-secondary)', fontSize: '0.88rem', marginBottom: '0.85rem' }}>
                      ✅ Scan complete! Review {lowConfPurchases.length} low-confidence items below, then finish setup.
                    </p>
                    <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
                      {lowConfPurchases.length > 0 && (
                        <button className="btn btn-secondary btn-sm" onClick={() => {
                          setFilterConf('low')
                          completeOnboarding()
                        }}>
                          Review Low-Confidence Items
                        </button>
                      )}
                      <button className="btn btn-primary btn-sm" onClick={completeOnboarding}>
                        Finish Setup ✓
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Top bar */}
            <div className="dashboard-topbar">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <UserChip email={userEmail} />
              </div>
              <button id="btn-fetch-emails" className="btn btn-primary" onClick={handleFetchEmails} disabled={fetchLoading}>
                {fetchLoading ? <><span className="spinner" /> Scanning inbox…</> : '🔍 Scan Inbox'}
              </button>
            </div>

            {fetchResult && (
              <div className="notice success fade-in" style={{ marginBottom: '1rem' }}>
                Scanned {fetchResult.emails_scanned} emails · Saved {fetchResult.purchases_created} new records
                {fetchResult.purchases_failed > 0 && ` · ${fetchResult.purchases_failed} skipped`}
              </div>
            )}
            {fetchError && <div className="notice error" style={{ marginBottom: '1rem' }}>Scan failed: {fetchError}</div>}

            {/* Stats */}
            {purchasesLoading ? <SkeletonStats /> : (
              <SummaryStats
                purchases={purchases}
                alerts={alerts}
                onAlerts={() => setScreen('alerts')}
              />
            )}

            {/* Timeline */}
            {!purchasesLoading && purchases.length > 0 && (
              <WarrantyTimeline purchases={purchases} onSelect={openItemDetail} />
            )}

            {/* Search + Filters */}
            {!purchasesLoading && purchases.length > 0 && (
              <>
                <div className="search-filter-bar">
                  <div className="search-wrap">
                    <span className="search-icon">🔍</span>
                    <input
                      id="search-input"
                      className="input"
                      type="search"
                      placeholder="Search products, brands…"
                      value={searchQ}
                      onChange={e => setSearchQ(e.target.value)}
                    />
                  </div>
                  <div className="filter-group">
                    <div className="select-wrap">
                      <select className="select" value={filterBrand} onChange={e => setFilterBrand(e.target.value)}>
                        <option value="">All Brands</option>
                        {uniqueBrands.map(b => <option key={b} value={b}>{b}</option>)}
                      </select>
                    </div>
                    <div className="select-wrap">
                      <select className="select" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
                        <option value="">All Status</option>
                        <option value="safe">Safe (&gt;30d)</option>
                        <option value="expiring">Expiring Soon</option>
                        <option value="overdue">Overdue</option>
                      </select>
                    </div>
                    <div className="select-wrap">
                      <select className="select" value={filterConf} onChange={e => setFilterConf(e.target.value)}>
                        <option value="">All Confidence</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Active filter chips */}
                {hasActiveFilters && (
                  <div className="active-filters">
                    {searchQ && <span className="filter-chip">Search: "{searchQ}" <span className="filter-chip-x" onClick={() => setSearchQ('')}>×</span></span>}
                    {filterBrand && <span className="filter-chip">Brand: {filterBrand} <span className="filter-chip-x" onClick={() => setFilterBrand('')}>×</span></span>}
                    {filterStatus && <span className="filter-chip">Status: {filterStatus} <span className="filter-chip-x" onClick={() => setFilterStatus('')}>×</span></span>}
                    {filterConf && <span className="filter-chip">Confidence: {filterConf} <span className="filter-chip-x" onClick={() => setFilterConf('')}>×</span></span>}
                    <span className="filter-chip" onClick={clearFilters} style={{ cursor: 'pointer' }}>Clear all ×</span>
                  </div>
                )}
              </>
            )}

            {/* Controls row */}
            {!purchasesLoading && purchases.length > 0 && (
              <div className="dashboard-controls">
                <div className="controls-left">
                  <span className="results-count">
                    {filteredPurchases.length} of {purchases.length} items
                  </span>
                </div>
                <div className="controls-right">
                  <div className="select-wrap" style={{ minWidth: 160 }}>
                    <select className="select" style={{ padding: '0.42rem 2rem 0.42rem 0.75rem', fontSize: '0.82rem' }}
                      value={sortBy} onChange={e => setSortBy(e.target.value)}>
                      <option value="date_desc">Newest First</option>
                      <option value="date_asc">Oldest First</option>
                      <option value="warranty_asc">Expiring Soonest</option>
                      <option value="price_desc">Highest Price</option>
                      <option value="name_asc">Name A–Z</option>
                    </select>
                  </div>
                  <div className="view-toggle">
                    <button
                      className={`view-toggle-btn ${viewMode === 'card' ? 'active' : ''}`}
                      onClick={() => setViewMode('card')} title="Card view" aria-label="Card view"
                    >⊞</button>
                    <button
                      className={`view-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
                      onClick={() => setViewMode('list')} title="List view" aria-label="List view"
                    >☰</button>
                  </div>
                </div>
              </div>
            )}

            {/* Content */}
            {purchasesLoading && <SkeletonGrid />}
            {purchasesError && (
              <div className="notice error">Could not load purchases: {purchasesError}</div>
            )}

            {!purchasesLoading && purchases.length === 0 && (
              <div className="empty-state">
                <div className="empty-state-icon">📭</div>
                <div className="empty-state-title">No purchases tracked yet</div>
                <div className="empty-state-sub">
                  Click "Scan Inbox" to import Gmail orders, or upload a document.
                </div>
                <button className="btn btn-primary" onClick={() => setScreen('upload')}>
                  Upload a Document
                </button>
              </div>
            )}

            {!purchasesLoading && filteredPurchases.length === 0 && purchases.length > 0 && (
              <div className="empty-state">
                <div className="empty-state-icon">🔍</div>
                <div className="empty-state-title">No results</div>
                <div className="empty-state-sub">Try adjusting your search or filters.</div>
                <button className="btn btn-secondary" onClick={clearFilters}>Clear Filters</button>
              </div>
            )}

            {/* Card grid or List */}
            {!purchasesLoading && filteredPurchases.length > 0 && viewMode === 'card' && (
              <div className="purchase-grid">
                {filteredPurchases.map(p => (
                  <PurchaseCard key={p.id} purchase={p} onSelect={openItemDetail} />
                ))}
              </div>
            )}
            {!purchasesLoading && filteredPurchases.length > 0 && viewMode === 'list' && (
              <div className="purchase-list">
                {filteredPurchases.map(p => (
                  <PurchaseListItem key={p.id} purchase={p} onSelect={openItemDetail} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* ════════════════════════════════════════════════════
            SCREEN: Item Detail
            ════════════════════════════════════════════════════ */}
        {screen === 'detail' && selectedPurchase && (
          <div className="screen-content fade-in">
            <button className="back-btn" onClick={() => { setScreen('dashboard'); setEditMode(false) }}>
              ← Back to Dashboard
            </button>

            <div className="card card-glow">
              <div className="detail-header">
                <div>
                  <div className="detail-product">{fmt(selectedPurchase.product_name, 'Unnamed Product')}</div>
                  <div className="detail-sub">
                    {fmt(selectedPurchase.retailer || selectedPurchase.brand, 'Unknown')}
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
                    <button className="btn btn-secondary" onClick={() => {
                      setEditMode(true)
                      setEditForm({
                        ...selectedPurchase,
                        warranty_end_date: selectedPurchase.warranty_period?.warranty_end_date || '',
                        return_window_end_date: selectedPurchase.warranty_period?.return_window_end_date || '',
                      })
                    }}>
                      ✏️ Edit Details
                    </button>
                    <button className="btn btn-danger" onClick={() => handleDeletePurchase(selectedPurchase.id)}>
                      🗑 Delete
                    </button>
                  </div>
                </>
              ) : (
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
                    <button className="btn btn-secondary" onClick={() => { setEditMode(false); setEditError(null) }}>Cancel</button>
                  </div>
                </div>
              )}
            </div>

            {/* Agent chat */}
            <div className="card" style={{ marginTop: '1rem' }}>
              <div className="card-header">
                <div className="card-icon violet">🤖</div>
                <div>
                  <div className="card-title">Ask the Warranty Agent</div>
                  <div className="card-subtitle">Natural-language questions about your purchases</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  id="agent-question-input" className="input" type="text" value={agentQuestion}
                  onChange={e => setAgentQuestion(e.target.value)}
                  placeholder={`e.g. "When does my ${selectedPurchase.product_name?.split(' ')[0] || 'product'} warranty expire?"`}
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

        {/* ════════════════════════════════════════════════════
            SCREEN: Alerts
            ════════════════════════════════════════════════════ */}
        {screen === 'alerts' && (
          <div className="screen-content fade-in">
            <div className="screen-header">
              <h2>🔔 Upcoming Alerts</h2>
              <button className="btn btn-secondary btn-sm" onClick={loadAlerts}>Refresh</button>
            </div>

            {alertsLoading && (
              <div className="alerts-list">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="skeleton-card" style={{ height: 72 }} />
                ))}
              </div>
            )}

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
                    <div className="alert-card-left"><AlertTypeIcon type={alert.alert_type} /></div>
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
                    <button className="btn btn-secondary btn-sm" onClick={() => {
                      const p = purchases.find(x => x.id === alert.purchase_id)
                      if (p) openItemDetail(p)
                    }}>View</button>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════
            SCREEN: Upload
            ════════════════════════════════════════════════════ */}
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

              <div
                className={`file-zone ${dragover ? 'dragover' : ''}`}
                onDragOver={e => { e.preventDefault(); setDragover(true) }}
                onDragLeave={() => setDragover(false)}
                onDrop={e => { e.preventDefault(); setDragover(false); const f = e.dataTransfer.files?.[0]; if (f) setUploadFile(f) }}
                onClick={() => fileInputRef.current?.click()}
              >
                <input id="upload-file-input" ref={fileInputRef} type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.webp,.tiff"
                  onChange={e => setUploadFile(e.target.files?.[0])}
                  style={{ display: 'none' }}
                />
                <div className="file-zone-icon">{uploadFile ? '📎' : '☁️'}</div>
                {uploadFile
                  ? <div className="file-zone-selected">{uploadFile.name}</div>
                  : <div className="file-zone-text">Drag &amp; drop or <strong>click to browse</strong></div>
                }
                <div className="file-zone-hint">PDF, JPEG, PNG, WEBP, TIFF · max 20 MB</div>
              </div>

              {uploadLoading && uploadProgress > 0 && (
                <div className="upload-progress-wrap">
                  <div className="upload-progress-bar" style={{ width: `${uploadProgress}%` }} />
                </div>
              )}

              <button
                id="btn-upload" className="btn btn-accent btn-full" style={{ marginTop: '0.75rem' }}
                onClick={handleUpload} disabled={!uploadFile || uploadLoading}
              >
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

        {/* ════════════════════════════════════════════════════
            SCREEN: Quick Lookup
            ════════════════════════════════════════════════════ */}
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
              <textarea
                id="extraction-test-input" className="textarea" rows={6} value={testText}
                onChange={e => setTestText(e.target.value)}
                placeholder={`Paste your order confirmation here, e.g.:\n\nDear Customer,\nThank you for your order from Amazon.in\nOrder #405-9812345 placed on 15 August 2025.\n1 x Sony WH-1000XM5 Headphones · ₹28,990 · 1-year warranty.`}
                style={{ resize: 'vertical', minHeight: '140px', marginBottom: '0.75rem', fontFamily: 'monospace', fontSize: '0.82rem' }}
              />
              <button
                id="btn-test-extraction" className="btn btn-secondary btn-full"
                onClick={handleExtractionTest} disabled={!testText.trim() || testLoading}
              >
                {testLoading ? <><span className="spinner" /> Analysing…</> : 'Extract Warranty Details'}
              </button>
              {testError && <div className="notice error" style={{ marginTop: '0.75rem' }}>{testError}</div>}
              {testResult && (
                <div className="fade-in" style={{ marginTop: '1rem' }}>
                  <ResultGrid result={testResult} />
                </div>
              )}
            </div>

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
                  <input
                    id="agent-question-lookup" className="input" type="text" value={agentQuestion}
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

        {/* Footer */}
        <footer className="footer">
          <div className="footer-inner">
            <div className="footer-brand"><span>🛡️</span><span>Warranty Radar</span></div>
            <div style={{ color: 'var(--clr-text-secondary)', fontSize: '0.78rem' }}>
              Protecting purchases across 10+ Indian retailers
            </div>
            <div>© {new Date().getFullYear()} Warranty Radar · v0.4.0</div>
          </div>
        </footer>

      </div>
    </>
  )
}
