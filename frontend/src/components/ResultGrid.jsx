import { motion } from 'motion/react'
import { ConfidenceBadge } from './ui'
import { fmt, fmtDate, fmtPrice } from '../lib/format'
import Icon from './Icon'

export default function ResultGrid({ result, ocrUsed }) {
  if (!result) return null

  const items = [
    { label: 'Product Name', value: fmt(result.product_name) },
    { label: 'Brand', value: fmt(result.brand) },
    { label: 'Retailer', value: fmt(result.retailer) },
    { label: 'Purchase Date', value: fmtDate(result.purchase_date) },
    { label: 'Amount Paid', value: fmtPrice(result.price), highlight: true },
    {
      label: 'Warranty Period',
      value: result.warranty_period_months ? `${result.warranty_period_months} months` : '—',
    },
    {
      label: 'Return Window',
      value: result.return_window_days ? `${result.return_window_days} days` : '—',
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-4"
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {items.map(item => (
          <div key={item.label} className="glass rounded-xl p-3">
            <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">
              {item.label}
            </div>
            <div className={`mt-1 text-sm font-semibold truncate ${item.highlight ? 'text-cyan-glow text-base' : 'text-fg'}`}>
              {item.value}
            </div>
          </div>
        ))}

        <div className="glass rounded-xl p-3">
          <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">Accuracy</div>
          <div className="mt-1">
            <ConfidenceBadge confidence={result.confidence || 'low'} />
          </div>
        </div>
      </div>

      {ocrUsed && (
        <div className="glass flex items-center gap-2 rounded-xl px-4 py-2 text-xs text-muted">
          <Icon name="file" size={15} className="text-cyan-glow" />
          <span>Document parsed using optical character recognition (OCR) intelligence.</span>
        </div>
      )}
    </motion.div>
  )
}

