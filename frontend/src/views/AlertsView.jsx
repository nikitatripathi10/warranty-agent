import { useState, useMemo } from 'react'
import { motion } from 'motion/react'
import { GlassCard, Button, EmptyState, Skeleton, containerStagger, itemRise } from '../components/ui'
import { fmt, fmtDate, urgencyColor } from '../lib/format'
import Icon from '../components/Icon'

export default function AlertsView({
  alerts,
  alertsLoading,
  onRefresh,
  purchases,
  onSelectPurchase,
}) {
  const [filterType, setFilterType] = useState('all')

  const filteredAlerts = useMemo(() => {
    if (filterType === 'all') return alerts
    return alerts.filter(a => a.alert_type === filterType)
  }, [alerts, filterType])

  const typeDetails = {
    return_window_expiry: { name: 'Return Window Expiry', icon: 'refresh', color: 'text-amber-400' },
    warranty_expiry: { name: 'Warranty Expiry', icon: 'shieldCheck', color: 'text-cyan-glow' },
    recall: { name: 'Product Recall Notice', icon: 'alert', color: 'text-rose-400' },
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-display text-2xl font-bold tracking-tight text-fg sm:text-3xl">
            Notifications &amp; Expiry Alerts
          </h2>
          <p className="mt-1 text-xs text-muted">
            Prioritized timeline of expiring return windows, factory warranties, and recalls.
          </p>
        </div>

        <Button variant="secondary" size="sm" onClick={onRefresh} disabled={alertsLoading}>
          <Icon name="refresh" size={15} />
          <span>Refresh Feed</span>
        </Button>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2">
        {[
          { id: 'all', label: `All Alerts (${alerts.length})` },
          { id: 'return_window_expiry', label: 'Return Windows' },
          { id: 'warranty_expiry', label: 'Warranties' },
          { id: 'recall', label: 'Recalls' },
        ].map(tab => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setFilterType(tab.id)}
            className={`rounded-xl px-3.5 py-1.5 text-xs font-semibold transition ${
              filterType === tab.id
                ? 'bg-violet-glow/30 text-fg border border-violet-glow/40 shadow-sm'
                : 'glass text-subtle hover:text-fg'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Alerts Feed */}
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
          sub="All your purchased products are in good standing for the next 60 days."
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
              critical: 'border-rose-400/50 bg-rose-500/5 hover:border-rose-400/80',
              warning: 'border-amber-400/50 bg-amber-500/5 hover:border-amber-400/80',
              overdue: 'border-rose-600/50 bg-rose-950/20 hover:border-rose-500/80',
              safe: 'border-cyan-glow/30 hover:border-cyan-glow/60',
            }[urgency] || 'border-line'

            return (
              <motion.div key={alert.alert_id} variants={itemRise}>
                <GlassCard
                  className={`p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between transition-all ${alertBorder}`}
                  intensity={0.1}
                >
                  <div className="flex items-start gap-3.5">
                    <div className={`grid size-10 shrink-0 place-items-center rounded-xl bg-glass ${details.color}`}>
                      <Icon name={details.icon} size={20} />
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-fg">
                        {fmt(alert.product_name, 'Unknown Product')}
                      </h4>
                      <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-subtle">
                        <span className="font-medium text-muted">{fmt(alert.retailer || alert.brand)}</span>
                        <span>·</span>
                        <span className="font-medium text-fg">{details.name}</span>
                        <span>·</span>
                        {alert.is_overdue ? (
                          <span className="font-semibold text-rose-400">
                            Overdue by {Math.abs(alert.days_until)} days
                          </span>
                        ) : alert.days_until === 0 ? (
                          <span className="font-semibold text-amber-400">Due today!</span>
                        ) : (
                          <span>
                            Due in {alert.days_until} day{alert.days_until !== 1 ? 's' : ''} ({fmtDate(alert.fire_date)})
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
                      <span>View Purchase</span>
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
  )
}

