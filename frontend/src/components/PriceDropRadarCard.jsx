import { useState, useEffect, useCallback } from 'react'
import { GlassCard, Button, Spinner } from './ui'
import Icon from './Icon'
import { fmtPrice } from '../lib/format'

export default function PriceDropRadarCard({
  purchase,
  apiBase,
  userId,
  addToast = () => {},
}) {
  const [radar, setRadar] = useState(null)
  const [loading, setLoading] = useState(false)
  const [customPrice, setCustomPrice] = useState('')
  const [copied, setCopied] = useState(false)

  const fetchRadar = useCallback(async (salePrice = null) => {
    if (!purchase?.id || !userId) return
    setLoading(true)
    try {
      const q = salePrice ? `&sale_price=${encodeURIComponent(salePrice)}` : ''
      const res = await fetch(
        `${apiBase}/purchases/${purchase.id}/price-radar?user_id=${encodeURIComponent(userId)}${q}`
      )
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setRadar(data)
    } catch (err) {
      console.warn('Could not load price radar:', err.message)
    } finally {
      setLoading(false)
    }
  }, [purchase?.id, userId, apiBase])

  useEffect(() => {
    fetchRadar()
  }, [fetchRadar])

  const handleAdjustPrice = e => {
    e.preventDefault()
    const p = parseFloat(customPrice)
    if (!isNaN(p) && p > 0) {
      fetchRadar(p)
    }
  }

  const copyScript = () => {
    if (!radar?.refund_request_message) return
    navigator.clipboard.writeText(radar.refund_request_message)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    addToast('Customer support price-match script copied to clipboard!', 'success')
  }

  if (!radar && !loading) return null

  return (
    <GlassCard className="p-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-line pb-4">
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-cyan-glow/20 text-cyan-glow ring-1 ring-cyan-glow/30">
            <Icon name="radar" size={20} />
          </span>
          <div>
            <h3 className="text-base font-semibold text-fg">Festival Price Drop &amp; Refund Radar</h3>
            <p className="text-xs text-muted">
              Diwali &amp; sale price monitoring with 1-click refund script
            </p>
          </div>
        </div>

        {radar && (
          <div className="flex items-center gap-2">
            {radar.is_return_window_active ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-400/15 px-3 py-1 text-xs font-semibold text-emerald-300 ring-1 ring-emerald-400/30">
                <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Active Return Window ({radar.days_left_in_return_window}d left)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-400/15 px-3 py-1 text-xs font-semibold text-amber-300 ring-1 ring-amber-400/30">
                <Icon name="clock" size={13} />
                Return Window Ended · Goodwill Claim
              </span>
            )}
          </div>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8 text-xs text-muted gap-2">
          <Spinner size={16} />
          <span>Scanning sale pricing…</span>
        </div>
      ) : radar ? (
        <div className="mt-5 space-y-5">
          {/* Price Metrics Grid */}
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="glass rounded-xl p-3 text-center">
              <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">
                Original Price
              </div>
              <div className="mt-1 text-base font-bold text-fg">
                {fmtPrice(radar.original_price)}
              </div>
            </div>

            <div className="glass rounded-xl p-3 text-center">
              <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">
                Festival Sale Price
              </div>
              <div className="mt-1 text-base font-bold text-muted">
                {fmtPrice(radar.current_sale_price)}
              </div>
            </div>

            <div className="glass rounded-xl p-3 text-center border border-cyan-glow/30 bg-cyan-glow/5">
              <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-cyan-glow">
                Potential Refund / Savings
              </div>
              <div className="mt-1 text-xl font-extrabold text-cyan-glow">
                {fmtPrice(radar.price_drop_amount)}
                <span className="ml-1 text-xs font-medium text-cyan-300/80">({radar.discount_percentage}%)</span>
              </div>
            </div>
          </div>

          {/* Interactive Live Price Adjuster */}
          <form onSubmit={handleAdjustPrice} className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-subtle">Spotted a lower live sale price?</span>
            <div className="flex items-center gap-2">
              <input
                type="number"
                step="any"
                value={customPrice}
                onChange={e => setCustomPrice(e.target.value)}
                placeholder="Enter price (₹)"
                className="w-32 rounded-lg border border-line bg-field px-3 py-1 text-xs text-fg outline-none focus:border-cyan-glow"
              />
              <button
                type="submit"
                className="rounded-lg bg-cyan-glow/20 px-3 py-1 font-medium text-cyan-200 hover:bg-cyan-glow/30 transition"
              >
                Update
              </button>
            </div>
          </form>

          {/* Pre-formatted Refund Negotiation Script */}
          <div className="rounded-xl border border-line bg-field/60 p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-subtle">
                1-Click Customer Support Price-Match Script
              </span>
              <button
                type="button"
                onClick={copyScript}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-glow hover:underline transition"
              >
                <Icon name={copied ? 'check' : 'copy'} size={14} />
                <span>{copied ? 'Copied!' : 'Copy Script'}</span>
              </button>
            </div>
            <p className="font-mono text-xs text-muted leading-relaxed whitespace-pre-wrap select-all">
              {radar.refund_request_message}
            </p>
          </div>

          {/* Action Footer */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <div className="text-[0.68rem] text-muted">
              {radar.is_return_window_active
                ? 'Tip: E-commerce platforms routinely issue price difference credits rather than processing full returns.'
                : 'Tip: Customer support agents can issue Amazon Pay / Flipkart Gift cards as goodwill gestures.'}
            </div>

            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={copyScript}>
                <Icon name={copied ? 'check' : 'copy'} size={14} />
                <span>{copied ? 'Copied' : 'Copy Script'}</span>
              </Button>
              <a
                href={radar.direct_support_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-glow/20 px-4 py-2 text-xs font-semibold text-cyan-glow hover:bg-cyan-glow/30 transition"
              >
                <span>Open {purchase.retailer || 'Retailer'} Chat</span>
                <Icon name="externalLink" size={13} />
              </a>
            </div>
          </div>
        </div>
      ) : null}
    </GlassCard>
  )
}
