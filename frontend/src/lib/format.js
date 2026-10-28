// ── Formatters (moved verbatim from the previous App.jsx) ─────────────────────
export function fmt(value, fallback = '—') {
  if (value === null || value === undefined || value === '') return fallback
  return String(value)
}
export function fmtPrice(price) {
  if (!price) return '—'
  return `₹${Number(price).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
}
export function fmtDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}
export function daysUntil(dateStr) {
  if (!dateStr) return null
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr + 'T00:00:00')
  return Math.round((target - today) / 86400000)
}
export function urgencyColor(days) {
  if (days === null) return ''
  if (days < 0)  return 'overdue'
  if (days <= 7) return 'critical'
  if (days <= 30) return 'warning'
  return 'safe'
}
export function urgencyLabel(days, type) {
  if (days === null) return null
  if (days < 0) return `${type} expired ${Math.abs(days)}d ago`
  if (days === 0) return `${type} expires today!`
  if (days === 1) return `${type} expires tomorrow`
  return `${type} in ${days}d`
}

// ── Compact helpers for the dashboard ─────────────────────────────────────────
export function fmtCompactINR(value) {
  const n = Number(value) || 0
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(2)}Cr`
  if (n >= 100000) return `₹${(n / 100000).toFixed(2)}L`
  if (n >= 1000) return `₹${(n / 1000).toFixed(1)}K`
  return `₹${n.toFixed(0)}`
}

/** The most urgent number of days across a purchase's return window / warranty end. */
export function mostUrgentDays(purchase) {
  const wp = purchase.warranty_period
  const ds = [wp?.return_window_end_date, wp?.warranty_end_date]
    .filter(Boolean)
    .map(daysUntil)
    .filter(d => d !== null)
  return ds.length ? Math.min(...ds) : null
}

/** Warranty health bucket used by charts: safe | warning | critical | expired | unknown */
export function warrantyBucket(purchase) {
  const d = purchase.warranty_period?.warranty_end_date
  if (!d) return 'unknown'
  const days = daysUntil(d)
  if (days === null) return 'unknown'
  if (days < 0) return 'expired'
  if (days <= 7) return 'critical'
  if (days <= 30) return 'warning'
  return 'safe'
}

export function greeting() {
  const h = new Date().getHours()
  if (h < 5) return 'Working late'
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

