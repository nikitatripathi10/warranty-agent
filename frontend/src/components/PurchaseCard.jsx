import { motion } from 'motion/react'
import { fmt, fmtDate, fmtPrice, daysUntil, urgencyColor, urgencyLabel, parseAdditionalWarranty } from '../lib/format'
import { ConfidenceBadge, UrgencyChip, GlassCard } from './ui'
import Icon from './Icon'

export default function PurchaseCard({ purchase, onSelect, onDelete }) {
  const wp = purchase.warranty_period
  const { additionalWarranty } = parseAdditionalWarranty(wp?.source_snippet)
  const returnDays = wp?.return_window_end_date ? daysUntil(wp.return_window_end_date) : null
  const warrantyDays = wp?.warranty_end_date ? daysUntil(wp.warranty_end_date) : null
  const urgentDays = [returnDays, warrantyDays].filter(d => d !== null)
  const mostUrgent = urgentDays.length > 0 ? Math.min(...urgentDays) : null
  const urgency = mostUrgent !== null ? urgencyColor(mostUrgent) : 'safe'

  const borderAccent = {
    critical: 'hover:border-rose-400/60 hover:shadow-[0_16px_40px_-12px_rgba(244,63,94,0.35)]',
    warning: 'hover:border-amber-400/60 hover:shadow-[0_16px_40px_-12px_rgba(245,158,11,0.35)]',
    overdue: 'hover:border-rose-500/40 hover:shadow-[0_16px_40px_-12px_rgba(244,63,94,0.25)]',
    safe: 'hover:border-cyan-glow/50 hover:shadow-[0_16px_40px_-12px_rgba(34,211,238,0.35)]',
  }[urgency] || 'hover:border-violet-glow/50'

  return (
    <motion.div
      whileHover={{ y: -4, scale: 1.01 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: 'spring', stiffness: 350, damping: 25 }}
      onClick={() => onSelect(purchase)}
      role="button"
      tabIndex={0}
      onKeyDown={e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect(purchase)
        }
      }}
      className="group outline-none"
    >
      <GlassCard
        className={`h-full p-5 flex flex-col justify-between cursor-pointer border-line transition-all duration-300 ${borderAccent}`}
        intensity={0.12}
      >
        <div>
          {/* Header row: Source icon, retailer, and confidence badge */}
          <div className="mb-3 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 truncate">
              <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-glass text-base">
                {purchase.source_type === 'email' ? '📧' : '📄'}
              </span>
              <span className="truncate text-xs font-semibold uppercase tracking-wider text-muted">
                {fmt(purchase.retailer || purchase.brand, '')}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <ConfidenceBadge confidence={wp?.confidence_score || 'low'} />
              {onDelete && (
                <button
                  type="button"
                  title="Delete purchase record"
                  aria-label="Delete purchase record"
                  onClick={e => {
                    e.stopPropagation()
                    onDelete(purchase.id)
                  }}
                  className="grid size-7 place-items-center rounded-lg border border-transparent text-subtle transition hover:border-rose-400/40 hover:bg-rose-500/15 hover:text-rose-300"
                >
                  <Icon name="trash" size={14} />
                </button>
              )}
            </div>
          </div>

          {/* Product Title */}
          <h4 className="mb-2 text-base font-semibold leading-snug text-fg transition-colors group-hover:text-cyan-glow line-clamp-2">
            {fmt(purchase.product_name, '')}
          </h4>

          {/* Purchase details */}
          <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-subtle">
            {purchase.purchase_date && (
              <span className="inline-flex items-center gap-1.5">
                <Icon name="calendar" size={13} />
                <span>{fmtDate(purchase.purchase_date)}</span>
              </span>
            )}
            {purchase.price && (
              <span className="inline-flex items-center gap-1 font-semibold text-fg">
                <Icon name="rupee" size={13} className="text-cyan-glow" />
                <span>{fmtPrice(purchase.price)}</span>
              </span>
            )}
            {purchase.family_member && (
              <span className="rounded-md bg-glass px-2 py-0.5 text-[0.68rem] text-muted">
                👤 {purchase.family_member}
              </span>
            )}
          </div>
        </div>

        {/* Footer: Expiry urgency indicators & estimated badge */}
        <div className="border-t border-line/60 pt-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-1.5">
              {returnDays !== null && (
                <UrgencyChip days={returnDays} label={urgencyLabel(returnDays, 'Return')} />
              )}
              {warrantyDays !== null && (
                <UrgencyChip days={warrantyDays} label={urgencyLabel(warrantyDays, 'Warranty')} />
              )}
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {additionalWarranty && (
                <span className="rounded bg-cyan-glow/15 px-1.5 py-0.5 text-[0.65rem] font-medium text-cyan-300 ring-1 ring-cyan-glow/30">
                  + Extended Warranty
                </span>
              )}
              {wp?.is_estimated && (
                <span className="rounded bg-violet-glow/15 px-1.5 py-0.5 text-[0.65rem] font-medium text-violet-300 ring-1 ring-violet-glow/30">
                  Estimated
                </span>
              )}
            </div>
          </div>
        </div>
      </GlassCard>
    </motion.div>
  )
}

