import { motion } from 'motion/react'
import { ConfidenceBadge } from './ui'
import { fmt, fmtDate, fmtPrice, parseAdditionalWarranty } from '../lib/format'
import Icon from './Icon'

export default function ResultGrid({ result, ocrUsed }) {
  if (!result) return null

  const { additionalWarranty } = parseAdditionalWarranty(result.source_snippet)
  const extDetails = result.additional_warranty_details || additionalWarranty

  const items = [
    { label: 'Product Name', value: fmt(result.product_name) },
    { label: 'Brand', value: fmt(result.brand) },
    { label: 'Retailer', value: fmt(result.retailer) },
    { label: 'Purchase Date', value: fmtDate(result.purchase_date) },
    { label: 'Amount Paid', value: fmtPrice(result.price), highlight: true },
    {
      label: 'Total Warranty Period',
      value: result.warranty_period_months ? `${result.warranty_period_months} months` : '—',
    },
    {
      label: 'Return Window',
      value: result.return_window_days ? `${result.return_window_days} days` : '—',
    },
  ]

  if (result.additional_warranty_months || extDetails) {
    items.push({
      label: 'Additional / Extended Warranty',
      value: extDetails || `+${result.additional_warranty_months} months`,
      highlight: true,
    })
  }

  if (result.manufacturer_doc_name || result.additional_doc_name) {
    const docList = [
      result.manufacturer_doc_name ? `Standard: ${result.manufacturer_doc_name}` : null,
      result.additional_doc_name ? `Additional: ${result.additional_doc_name}` : null,
    ]
      .filter(Boolean)
      .join('\n')
    items.push({
      label: 'Uploaded Documents',
      value: docList,
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-4"
    >
      <div className="grid gap-3.5 sm:grid-cols-2">
        {items.map(item => (
          <div key={item.label} className="glass rounded-xl p-4">
            <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">
              {item.label}
            </div>
            <div
              className={`mt-1.5 text-sm font-semibold break-words whitespace-pre-line ${
                item.highlight ? 'text-cyan-glow font-bold' : 'text-fg'
              }`}
            >
              {item.value}
            </div>
          </div>
        ))}

        <div className="glass rounded-xl p-4">
          <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">
            Accuracy
          </div>
          <div className="mt-1.5">
            <ConfidenceBadge confidence={result.confidence || 'low'} suffix=" Accuracy" />
          </div>
        </div>
      </div>

      {ocrUsed && (
        <div className="glass flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs text-muted">
          <Icon name="file" size={15} className="text-cyan-glow" />
          <span>Text read from scanned image using optical character recognition (OCR).</span>
        </div>
      )}
    </motion.div>
  )
}
