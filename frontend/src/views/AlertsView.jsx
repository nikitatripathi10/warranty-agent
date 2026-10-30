import { useState, useMemo, useEffect, useCallback } from 'react'
import { motion } from 'motion/react'
import { GlassCard, Button, EmptyState, Skeleton, Spinner, containerStagger, itemRise } from '../components/ui'
import { fmt, fmtDate, urgencyColor } from '../lib/format'
import Icon from '../components/Icon'

export default function AlertsView({
  apiBase,
  userId,
  alerts,
  alertsLoading,
  onRefresh,
  purchases,
  onSelectPurchase,
  addToast,
}) {
  const [activeTab, setActiveTab] = useState('active') // 'active' | 'history' | 'recalls'
  const [filterType, setFilterType] = useState('all')

  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)

  const [recalls, setRecalls] = useState([])
  const [recallsLoading, setRecallsLoading] = useState(false)
  const [checkingRecalls, setCheckingRecalls] = useState(false)

  const loadHistory = useCallback(async () => {
    if (!apiBase || !userId) return
    setHistoryLoading(true)
    try {
      const res = await fetch(`${apiBase}/alerts/history?user_id=${encodeURIComponent(userId)}`)
      const data = await res.json()
      if (res.ok) setHistory(data.alerts || [])
    } catch {
      /* silent */
    } finally {
      setHistoryLoading(false)
    }
  }, [apiBase, userId])

  const loadRecalls = useCallback(async () => {
    if (!apiBase) return
    setRecallsLoading(true)
    try {
      const res = await fetch(`${apiBase}/alerts/recalls`)
      const data = await res.json()
      if (res.ok) setRecalls(Array.isArray(data) ? data : [])
    } catch {
      /* silent */
    } finally {
      setRecallsLoading(false)
    }
  }, [apiBase])

  useEffect(() => {
    if (activeTab === 'history') loadHistory()
    if (activeTab === 'recalls') loadRecalls()
  }, [activeTab, loadHistory, loadRecalls])

  async function handleRunRecallCheck() {
    if (!apiBase || !userId) return
    setCheckingRecalls(true)
    try {
      const res = await fetch(
        `${apiBase}/alerts/recall-check?user_id=${encodeURIComponent(userId)}`,
        { method: 'POST' }
      )
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      if (addToast) {
        addToast(
          `Checked ${data.purchases_checked} purchase${data.purchases_checked === 1 ? '' : 's'} · ${data.recall_matches} recall match${data.recall_matches === 1 ? '' : 'es'}`,
          data.recall_matches > 0 ? 'warning' : 'success'
        )
      }
      onRefresh?.()
      loadRecalls()
    } catch (err) {
      addToast?.(`Recall check failed: ${err.message}`, 'error')
    } finally {
      setCheckingRecalls(false)
    }
  }

  const filteredAlerts = useMemo(() => {
    if (filterType === 'all') return alerts
    return alerts.filter(a => a.alert_type === filterType)
  }, [alerts, filterType])

  const typeDetails = {
    return_window_expiry: { name: 'Return window closing', icon: 'refresh', color: 'text-amber-300' },
    warranty_expiry: { name: 'Warranty expiring', icon: 'shieldCheck', color: 'text-cyan-300' },
    recall: { name: 'Product recall notice', icon: 'alert', color: 'text-rose-300' },
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-display text-2xl font-bold tracking-tight text-fg sm:text-3xl">
            Alerts &amp; Recalls
          </h2>
          <p className="mt-1 text-xs text-muted">
            Upcoming return deadlines, warranty expirations, and product recall checks for your purchases.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleRunRecallCheck}
            disabled={checkingRecalls || !userId}
          >
            {checkingRecalls ? <Spinner size={14} /> : <Icon name="shieldCheck" size={15} />}
            <span>Check Recalls</span>
          </Button>
          <Button variant="secondary" size="sm" onClick={onRefresh} disabled={alertsLoading}>
            <Icon name="refresh" size={15} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* Primary Section Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-line pb-3">
        {[
          { id: 'active', label: `Upcoming (${alerts.length})`, icon: 'bell' },
          { id: 'history', label: 'Past Alerts', icon: 'clock' },
          { id: 'recalls', label: 'Product Recalls', icon: 'alert' },
        ].map(tab => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition ${
              activeTab === tab.id
                ? 'border border-violet-glow/35 bg-violet-glow/15 text-fg'
                : 'glass text-subtle hover:text-fg'
            }`}
          >
            <Icon name={tab.icon} size={15} />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* ── Upcoming Alerts Tab ── */}
      {activeTab === 'active' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {[
              { id: 'all', label: `All (${alerts.length})` },
              { id: 'return_window_expiry', label: 'Return windows' },
              { id: 'warranty_expiry', label: 'Warranties' },
              { id: 'recall', label: 'Recalls' },
            ].map(tab => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setFilterType(tab.id)}
                className={`rounded-xl px-3 py-1.5 text-xs font-medium transition ${
                  filterType === tab.id
                    ? 'border border-line-strong bg-white/10 text-fg'
                    : 'glass text-subtle hover:text-fg'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {alertsLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <GlassCard key={i} className="p-4">
                  <Skeleton className="h-12 w-full" />
                </GlassCard>
              ))}
            </div>
          ) : filteredAlerts.length === 0 ? (
            <EmptyState
              icon="check"
              title="No upcoming alerts"
              sub="When a return window or warranty expiration approaches, it will appear here."
            />
          ) : (
            <motion.div
              variants={containerStagger}
              initial="hidden"
              animate="show"
              className="space-y-3"
            >
              {filteredAlerts.map(alert => {
                const urgency = alert.is_overdue ? 'overdue' : urgencyColor(alert.days_until)
                const details = typeDetails[alert.alert_type] || {
                  name: alert.alert_type,
                  icon: 'bell',
                  color: 'text-violet-300',
                }

                const alertBorder = {
                  critical: 'border-rose-400/35 bg-rose-500/5',
                  warning: 'border-amber-400/35 bg-amber-500/5',
                  overdue: 'border-rose-500/40 bg-rose-950/15',
                  safe: 'border-line',
                }[urgency] || 'border-line'

                return (
                  <motion.div key={alert.alert_id} variants={itemRise}>
                    <GlassCard
                      className={`flex flex-col gap-3 p-4 transition-all sm:flex-row sm:items-center sm:justify-between ${alertBorder}`}
                      intensity={0.06}
                    >
                      <div className="flex items-start gap-3.5">
                        <div className={`grid size-10 shrink-0 place-items-center rounded-xl bg-glass ${details.color}`}>
                          <Icon name={details.icon} size={19} />
                        </div>
                        <div>
                          <h4 className="text-sm font-semibold text-fg">
                            {fmt(alert.product_name, 'Unnamed Product')}
                          </h4>
                          <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-subtle">
                            <span className="font-medium text-muted">{fmt(alert.retailer || alert.brand)}</span>
                            <span>·</span>
                            <span className="font-medium text-fg">{details.name}</span>
                            <span>·</span>
                            {alert.is_overdue ? (
                              <span className="font-semibold text-rose-300">
                                Overdue by {Math.abs(alert.days_until)} day{Math.abs(alert.days_until) !== 1 ? 's' : ''}
                              </span>
                            ) : alert.days_until === 0 ? (
                              <span className="font-semibold text-amber-300">Due today</span>
                            ) : (
                              <span>
                                In {alert.days_until} day{alert.days_until !== 1 ? 's' : ''} ({fmtDate(alert.fire_date)})
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 self-end sm:self-center">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            const p = purchases.find(x => x.id === alert.purchase_id)
                            if (p) onSelectPurchase(p)
                          }}
                        >
                          <span>View Item</span>
                          <Icon name="arrowRight" size={14} />
                        </Button>
                      </div>
                    </GlassCard>
                  </motion.div>
                )
              })}
            </motion.div>
          )}
        </div>
      )}

      {/* ── Past / Sent Alerts Tab ── */}
      {activeTab === 'history' && (
        <div className="space-y-3">
          {historyLoading ? (
            <GlassCard className="p-4">
              <Skeleton className="h-12 w-full" />
            </GlassCard>
          ) : history.length === 0 ? (
            <EmptyState
              icon="clock"
              title="No past alerts yet"
              sub="Alerts that have already been sent will be archived here."
            />
          ) : (
            history.map(item => {
              const details = typeDetails[item.alert_type] || {
                name: item.alert_type,
                icon: 'bell',
                color: 'text-muted',
              }
              return (
                <GlassCard key={item.alert_id} className="flex items-center justify-between gap-3 p-4" intensity={0.05}>
                  <div className="flex items-center gap-3">
                    <div className={`grid size-9 place-items-center rounded-xl bg-glass ${details.color}`}>
                      <Icon name={details.icon} size={17} />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-fg">{fmt(item.product_name, 'Unnamed Product')}</div>
                      <div className="text-xs text-subtle">
                        {details.name} · Fired {fmtDate(item.fire_date)}
                      </div>
                    </div>
                  </div>
                </GlassCard>
              )
            })
          )}
        </div>
      )}

      {/* ── Product Recalls Tab ── */}
      {activeTab === 'recalls' && (
        <div className="space-y-4">
          {recallsLoading ? (
            <GlassCard className="p-4">
              <Skeleton className="h-16 w-full" />
            </GlassCard>
          ) : recalls.length === 0 ? (
            <EmptyState
              icon="shieldCheck"
              title="No recall advisories recorded"
              sub="Use 'Check Recalls' above to scan your purchases against known manufacturer recall notices."
            />
          ) : (
            <div className="space-y-3">
              {recalls.map(rec => (
                <GlassCard key={rec.id} className="space-y-2 p-4" intensity={0.06}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-sm font-semibold text-fg">
                      {fmt(rec.brand)} {fmt(rec.product_model, '')}
                    </div>
                    {rec.date_found && (
                      <span className="text-xs text-subtle">{fmtDate(rec.date_found)}</span>
                    )}
                  </div>
                  {rec.description && (
                    <p className="text-xs leading-relaxed text-muted">{rec.description}</p>
                  )}
                  {rec.source_url && (
                    <a
                      href={rec.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-violet-300 hover:underline"
                    >
                      <span>View advisory source</span>
                      <Icon name="arrowRight" size={12} />
                    </a>
                  )}
                </GlassCard>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
