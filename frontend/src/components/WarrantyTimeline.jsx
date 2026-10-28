import { motion } from 'motion/react'
import { fmtDate, daysUntil, urgencyColor } from '../lib/format'
import { GlassCard } from './ui'
import Icon from './Icon'

export default function WarrantyTimeline({ purchases, onSelect }) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  // Build items with warranty and return end dates
  const items = purchases
    .flatMap(p => {
      const wp = p.warranty_period
      const arr = []
      if (wp?.warranty_end_date) {
        arr.push({
          purchase: p,
          date: wp.warranty_end_date,
          label: p.product_name || 'Product',
          type: 'warranty',
          retailer: p.retailer || p.brand || 'Retailer',
        })
      }
      if (wp?.return_window_end_date) {
        arr.push({
          purchase: p,
          date: wp.return_window_end_date,
          label: p.product_name || 'Product',
          type: 'return',
          retailer: p.retailer || p.brand || 'Retailer',
        })
      }
      return arr
    })
    .filter(x => x.date)

  if (items.length === 0) return null

  // Date range (30 days ago to +180 days)
  const windowDays = 180
  const startDate = new Date(today)
  startDate.setDate(startDate.getDate() - 20)
  const endDate = new Date(today)
  endDate.setDate(endDate.getDate() + windowDays)
  const totalRange = endDate - startDate

  const todayPct = Math.max(0, Math.min(100, ((today - startDate) / totalRange) * 100))

  return (
    <GlassCard className="mb-6 p-5 sm:p-6" intensity={0.12}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-lg bg-violet-glow/20 text-violet-300 ring-1 ring-line">
            <Icon name="calendar" size={16} />
          </span>
          <div>
            <h3 className="text-sm font-semibold text-fg">Active Coverage Timeline</h3>
            <p className="text-[0.68rem] text-subtle">Visual schedule for the next 6 months</p>
          </div>
        </div>
        <span className="text-[0.72rem] text-subtle">
          Showing <span className="font-semibold text-fg">{items.length}</span> coverage milestones
        </span>
      </div>

      {/* Timeline track container */}
      <div className="relative mt-3 mb-4 h-16 w-full rounded-xl border border-line bg-glass px-2 pt-2 pb-1 overflow-hidden">
        {/* Subtle grid lines at 30d intervals */}
        {[30, 60, 90, 120, 150].map(days => {
          const d = new Date(today)
          d.setDate(d.getDate() + days)
          const pct = ((d - startDate) / totalRange) * 100
          if (pct < 0 || pct > 100) return null
          return (
            <div
              key={days}
              className="pointer-events-none absolute inset-y-0 border-r border-line/40"
              style={{ left: `${pct}%` }}
            >
              <span className="absolute bottom-1 -translate-x-1/2 text-[0.6rem] font-mono text-subtle/70">
                +{days}d
              </span>
            </div>
          )
        })}

        {/* "Today" marker line */}
        <div
          className="pointer-events-none absolute inset-y-0 z-20 w-0.5 bg-gradient-to-b from-cyan-glow to-electric shadow-[0_0_12px_rgba(34,211,238,0.9)]"
          style={{ left: `${todayPct}%` }}
        >
          <span className="absolute top-1 left-1.5 rounded-sm bg-cyan-glow/20 px-1 py-0.2 text-[0.6rem] font-bold text-cyan-glow backdrop-blur-sm">
            Today
          </span>
        </div>

        {/* Milestone bars */}
        {items.map((item, idx) => {
          const itemDate = new Date(item.date + 'T00:00:00')
          const pct = ((itemDate - startDate) / totalRange) * 100
          if (pct < 0 || pct > 100) return null
          const days = daysUntil(item.date)
          const urgency = urgencyColor(days)

          const colors = {
            critical: 'from-rose-500/80 to-pink-600/80 border-rose-400 text-rose-100 shadow-[0_0_12px_rgba(244,63,94,0.6)]',
            warning: 'from-amber-500/80 to-yellow-600/80 border-amber-300 text-amber-100 shadow-[0_0_10px_rgba(245,158,11,0.5)]',
            overdue: 'from-zinc-700/80 to-zinc-800/80 border-zinc-600 text-zinc-300',
            safe: 'from-cyan-500/80 to-blue-600/80 border-cyan-300 text-cyan-100 shadow-[0_0_10px_rgba(34,211,238,0.4)]',
          }[urgency] || 'from-violet-500/80 to-indigo-600/80 border-violet-300 text-violet-100'

          return (
            <motion.button
              key={`${item.purchase.id}-${item.type}-${idx}`}
              type="button"
              whileHover={{ scale: 1.08, zIndex: 30 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => onSelect(item.purchase)}
              title={`${item.label} · ${item.type === 'warranty' ? 'Warranty' : 'Return'} ends ${fmtDate(item.date)}`}
              style={{
                left: `${Math.max(1, Math.min(94, pct))}%`,
                top: item.type === 'return' ? '18px' : '36px',
              }}
              className={`group absolute -translate-x-1/2 flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[0.62rem] font-medium bg-gradient-to-r ${colors} cursor-pointer transition`}
            >
              <span className="truncate max-w-[80px] sm:max-w-[120px]">
                {item.type === 'return' ? '🔄' : '🛡️'} {item.label.split(' ')[0]}
              </span>
            </motion.button>
          )
        })}
      </div>

      {/* Legend & hint */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-[0.7rem] text-subtle">
        <div className="flex flex-wrap items-center gap-4">
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-cyan-glow" /> Safe (&gt;30d)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-amber-400" /> Expiring soon (&lt;30d)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-rose-400" /> Critical (&lt;7d)
          </span>
        </div>
        <span className="italic">Click any bar to inspect item details</span>
      </div>
    </GlassCard>
  )
}

