import { useState, useEffect, useCallback } from 'react'
import { motion } from 'motion/react'
import { GlassCard, Spinner, Select } from './ui'
import Icon from './Icon'
import { cn } from '../lib/utils'

const TONES = {
  extended_warranty: {
    box: 'border-emerald-400/35 bg-emerald-400/10',
    chip: 'text-emerald-300',
    label: 'Extra cover possible',
  },
  purchase_protection_only: {
    box: 'border-sky-400/35 bg-sky-400/10',
    chip: 'text-sky-300',
    label: 'Purchase protection',
  },
  needs_card: {
    box: 'border-amber-400/35 bg-amber-400/10',
    chip: 'text-amber-300',
    label: 'Pick your card',
  },
  not_eligible: {
    box: 'border-line bg-glass/40',
    chip: 'text-muted',
    label: 'Not eligible',
  },
  no_known_benefit: {
    box: 'border-line bg-glass/40',
    chip: 'text-muted',
    label: 'No data for this card',
  },
}

/**
 * Credit-card benefit matcher for one purchase.
 *
 * Shows which credit card paid (found on the invoice, or picked by the user) and whether
 * that card may add a free extended warranty or purchase protection — with the extended
 * end date, conditions and claim steps. Wording is deliberately cautious ("may"): card
 * benefits vary by variant and change over time, so a disclaimer is always shown.
 */
export default function CardBenefitCard({ purchase, apiBase, userId, addToast }) {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const base = `${apiBase}/purchases/${purchase.id}`

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${base}/card-benefits?user_id=${encodeURIComponent(userId)}`)
      if (!res.ok) throw new Error('Could not load card benefits')
      setReport(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [base, userId])

  useEffect(() => {
    load()
  }, [load])

  const chooseCard = async cardKey => {
    setSaving(true)
    setError('')
    try {
      const res = await fetch(`${base}/payment-card`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, card_key: cardKey || null }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || 'Could not save your card')
      setReport(data)
      addToast?.(cardKey ? 'Card saved.' : 'Card choice cleared.', 'success')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const benefit = report?.benefit
  const detected = report?.detected_card
  const tone = TONES[benefit?.status] || TONES.not_eligible

  return (
    <GlassCard className="p-6">
      <div className="mb-4 flex items-center gap-3">
        <div className="grid size-10 place-items-center rounded-xl bg-amber-400/15 text-amber-300 ring-1 ring-line">
          <Icon name="creditCard" size={20} />
        </div>
        <div>
          <h3 className="text-base font-semibold text-fg">Credit card perks</h3>
          <p className="text-xs text-muted">
            Some premium cards add free extended warranty or purchase protection. Here&rsquo;s what yours may offer
            for this item.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-xs text-subtle">
          <Spinner size={14} />
          <span>Checking card benefits…</span>
        </div>
      ) : error && !report ? (
        <p className="text-xs text-rose-300">{error}</p>
      ) : report ? (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
            <div>
              <label
                htmlFor="card-select"
                className="mb-1.5 block text-xs font-medium tracking-wide text-muted uppercase"
              >
                Card used for this purchase
              </label>
              <Select
                id="card-select"
                value={detected?.card_key || ''}
                disabled={saving}
                onChange={e => chooseCard(e.target.value)}
                wrapClassName="w-full"
                className="w-full py-2.5"
              >
                <option value="">
                  {detected?.issuer_label ? `${detected.issuer_label} card — choose variant…` : 'Select the card…'}
                </option>
                {report.options.map(o => (
                  <option key={o.key} value={o.key}>
                    {o.label}
                  </option>
                ))}
              </Select>
            </div>
            {saving && <Spinner size={16} />}
          </div>

          {detected && (
            <p className="text-[0.72rem] text-subtle">
              {detected.source === 'manual' ? 'You selected this card' : 'Found on your invoice'}
              {detected.issuer_label ? ` · ${detected.issuer_label}` : ''}
              {detected.last4 ? ` · ending ${detected.last4}` : ''}
            </p>
          )}

          <motion.div
            key={benefit.status + (benefit.extended_warranty_end || '')}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn('rounded-xl border p-4', tone.box)}
          >
            <div className={cn('mb-1 text-[0.68rem] font-semibold uppercase tracking-wider', tone.chip)}>
              {tone.label}
            </div>
            <p className="text-sm font-medium leading-relaxed text-fg">{benefit.headline}</p>

            {benefit.status === 'extended_warranty' && benefit.extended_warranty_end && (
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <div className="glass rounded-lg p-2.5">
                  <div className="text-[0.65rem] uppercase tracking-wider text-subtle">Manufacturer warranty ends</div>
                  <div className="text-sm font-semibold text-fg">{benefit.manufacturer_warranty_end}</div>
                </div>
                <div className="glass rounded-lg p-2.5">
                  <div className="text-[0.65rem] uppercase tracking-wider text-subtle">Card cover may last until</div>
                  <div className="text-sm font-semibold text-emerald-300">{benefit.extended_warranty_end}</div>
                </div>
              </div>
            )}

            {benefit.protection_summary && (
              <p className="mt-3 text-xs leading-relaxed text-muted">{benefit.protection_summary}</p>
            )}
            {benefit.insurer && <p className="mt-1 text-xs text-muted">Insurer: {benefit.insurer}</p>}
          </motion.div>

          {benefit.conditions.length > 0 && (
            <details className="group rounded-xl border border-line bg-glass/30 p-3 text-xs text-muted">
              <summary className="cursor-pointer select-none font-semibold text-fg">Conditions to check</summary>
              <ul className="mt-2 list-disc space-y-1 pl-5 leading-relaxed">
                {benefit.conditions.map(c => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </details>
          )}

          {benefit.claim_steps.length > 0 && (
            <details className="group rounded-xl border border-line bg-glass/30 p-3 text-xs text-muted">
              <summary className="cursor-pointer select-none font-semibold text-fg">How to claim</summary>
              <ol className="mt-2 list-decimal space-y-1 pl-5 leading-relaxed">
                {benefit.claim_steps.map(s => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            </details>
          )}

          {error && <p className="text-xs text-rose-300">{error}</p>}
          <p className="text-[0.68rem] leading-relaxed text-subtle">{benefit.disclaimer}</p>
        </div>
      ) : null}
    </GlassCard>
  )
}

