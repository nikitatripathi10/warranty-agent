import { motion } from 'motion/react'
import { fmt, fmtDate, fmtPrice, daysUntil, urgencyLabel } from '../lib/format'
import { ConfidenceBadge, UrgencyChip } from './ui'
import Icon from './Icon'

export default function PurchaseListItem({ purchase, onSelect, onDelete }) {
  const wp = purchase.warranty_period
  const returnDays = wp?.return_window_end_date ? daysUntil(wp.return_window_end_date) : null
  const warrantyDays = wp?.warranty_end_date ? daysUntil(wp.warranty_end_date) : null

  return (
    <motion.div
      whileHover={{ scale: 1.006, x: 3 }}
      whileTap={{ scale: 0.99 }}
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
      className="glass hover:border-line-strong hover:bg-glass-hover group flex cursor-pointer flex-col gap-3 rounded-xl p-3.5 sm:flex-row sm:items-center sm:justify-between transition-all outline-none"
    >
      <div className="flex items-center gap-3 min-w-0">
        <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-glass text-lg">
          {purchase.source_type === 'email' ? '📧' : '📄'}
        </span>
        <div className="min-w-0">
          <h4 className="truncate text-sm font-semibold text-fg group-hover:text-cyan-glow transition-colors">
            {fmt(purchase.product_name, '')}
          </h4>
          <div className="flex flex-wrap items-center gap-x-3 text-xs text-subtle">
            <span className="font-medium text-muted">{fmt(purchase.retailer || purchase.brand, '')}</span>
            {purchase.purchase_date && <span>🗓 {fmtDate(purchase.purchase_date)}</span>}
            {purchase.price && <span className="font-semibold text-fg">💰 {fmtPrice(purchase.price)}</span>}
            {purchase.family_member && <span>👤 {purchase.family_member}</span>}
          </div>
        </div>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-2">
        {warrantyDays !== null && (
          <UrgencyChip days={warrantyDays} label={urgencyLabel(warrantyDays, 'Warranty')} />
        )}
        {returnDays !== null && (
          <UrgencyChip days={returnDays} label={urgencyLabel(returnDays, 'Return')} />
        )}
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
    </motion.div>
  )
}

