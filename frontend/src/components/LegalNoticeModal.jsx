import { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { GlassCard, Button, Spinner } from './ui'
import Icon from './Icon'

export default function LegalNoticeModal({
  purchase,
  apiBase,
  userId,
  userEmail,
  userName = '',
  isOpen,
  onClose,
  addToast = () => {},
}) {
  const [grievanceType, setGrievanceType] = useState('warranty_denial')
  const [issueDescription, setIssueDescription] = useState('')
  const [consumerName, setConsumerName] = useState(userName || '')
  const [consumerAddress, setConsumerAddress] = useState('')
  const [consumerPhone, setConsumerPhone] = useState('')
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState(null)
  const [copiedNotice, setCopiedNotice] = useState(false)
  const [copiedNch, setCopiedNch] = useState(false)

  if (!isOpen || !purchase) return null

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const res = await fetch(`${apiBase}/purchases/${purchase.id}/legal-notice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          grievance_type: grievanceType,
          issue_description: issueDescription.trim() || undefined,
          consumer_name: consumerName.trim() || undefined,
          consumer_address: consumerAddress.trim() || undefined,
          consumer_phone: consumerPhone.trim() || undefined,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setResult(data)
      addToast('Legal Notice and NCH Complaint successfully generated!', 'success')
    } catch (err) {
      addToast(`Failed to generate legal notice: ${err.message}`, 'error')
    } finally {
      setGenerating(false)
    }
  }

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text)
    if (type === 'notice') {
      setCopiedNotice(true)
      setTimeout(() => setCopiedNotice(false), 2000)
      addToast('15-Day Legal Demand Notice copied to clipboard!', 'success')
    } else {
      setCopiedNch(true)
      setTimeout(() => setCopiedNch(false), 2000)
      addToast('NCH 1915 grievance summary copied!', 'success')
    }
  }

  const downloadNotice = () => {
    if (!result?.legal_notice_text) return
    const blob = new Blob([result.legal_notice_text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `Legal_Notice_${(purchase.product_name || 'Product').replace(/\s+/g, '_')}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    addToast('Notice downloaded as text file.', 'info')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.96 }}
        className="w-full max-w-3xl my-8"
      >
        <GlassCard beam beamColors={['#f43f5e', '#a855f7']} className="p-6 sm:p-8 max-h-[88vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-start justify-between pb-4 border-b border-line">
            <div className="flex items-center gap-3">
              <span className="grid size-11 place-items-center rounded-xl bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/30">
                <Icon name="scale" size={22} />
              </span>
              <div>
                <h3 className="font-display text-xl font-bold text-fg">
                  1-Click Legal Notice &amp; Dispute Generator
                </h3>
                <p className="text-xs text-muted">
                  Consumer Protection Act 2019 · e-Daakhil Online Consumer Court · NCH 1915
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-subtle hover:text-fg hover:bg-glass transition"
            >
              <Icon name="x" size={18} />
            </button>
          </div>

          {/* Product context pill */}
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-glass px-4 py-2.5 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-fg">{purchase.product_name}</span>
              <span className="text-muted">·</span>
              <span className="text-subtle">{purchase.retailer || purchase.brand}</span>
            </div>
            {purchase.price && (
              <span className="font-bold text-cyan-glow">₹{Number(purchase.price).toLocaleString('en-IN')}</span>
            )}
          </div>

          {!result ? (
            /* Dispute Configuration Form */
            <div className="mt-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-subtle mb-1.5">
                  Nature of Grievance
                </label>
                <select
                  value={grievanceType}
                  onChange={e => setGrievanceType(e.target.value)}
                  className="w-full rounded-xl border border-line bg-field px-3.5 py-2.5 text-sm text-fg outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-400/20"
                >
                  <option value="warranty_denial">Unlawful Warranty Repudiation / Claim Rejected</option>
                  <option value="defective_product">Inherent Manufacturing Defect &amp; Refusal to Replace</option>
                  <option value="delayed_repair">Repair Delayed &gt; 30 Days / No Spare Parts Available</option>
                  <option value="unfair_trade_practice">False Warranty Assurances / Unfair Trade Practice</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-subtle mb-1.5">
                  Specific Defect / Details (Optional)
                </label>
                <textarea
                  rows={3}
                  value={issueDescription}
                  onChange={e => setIssueDescription(e.target.value)}
                  placeholder="e.g. Service center rejected claim claiming liquid damage without diagnostic proof. Job sheet #JS-98421."
                  className="w-full rounded-xl border border-line bg-field p-3 text-sm text-fg placeholder:text-subtle outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-400/20 resize-none"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-subtle mb-1.5">
                    Your Full Name
                  </label>
                  <input
                    type="text"
                    value={consumerName}
                    onChange={e => setConsumerName(e.target.value)}
                    placeholder="Complainant Name"
                    className="w-full rounded-xl border border-line bg-field px-3 py-2 text-sm text-fg outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-400/20"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-subtle mb-1.5">
                    Mobile Number (for NCH)
                  </label>
                  <input
                    type="tel"
                    value={consumerPhone}
                    onChange={e => setConsumerPhone(e.target.value)}
                    placeholder="98XXXXXXXX"
                    className="w-full rounded-xl border border-line bg-field px-3 py-2 text-sm text-fg outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-400/20"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-subtle mb-1.5">
                  Residential Address (City, State, PIN)
                </label>
                <input
                  type="text"
                  value={consumerAddress}
                  onChange={e => setConsumerAddress(e.target.value)}
                  placeholder="e.g. Flat 402, Green Heights, Indiranagar, Bengaluru 560038"
                  className="w-full rounded-xl border border-line bg-field px-3 py-2 text-sm text-fg outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-400/20"
                />
              </div>

              <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 text-xs text-subtle space-y-1">
                <div className="font-semibold text-rose-300 flex items-center gap-1.5">
                  <Icon name="info" size={14} />
                  <span>Statutory Grounding (Consumer Protection Act, 2019):</span>
                </div>
                <p>
                  Generates an enforceable 15-day pre-litigation notice holding the brand and seller jointly liable under
                  Sections 84-87 (Product Liability) and Section 2(11) (Deficiency in Service).
                </p>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <Button variant="secondary" size="md" onClick={onClose}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="md"
                  onClick={handleGenerate}
                  disabled={generating}
                  className="bg-rose-500 hover:bg-rose-600 text-white shadow-rose-500/25"
                >
                  {generating ? (
                    <>
                      <Spinner size={15} />
                      <span>Drafting Notice…</span>
                    </>
                  ) : (
                    <>
                      <Icon name="scale" size={16} />
                      <span>Generate Formal Notice &amp; NCH Draft</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          ) : (
            /* Results View */
            <div className="mt-6 space-y-6">
              {/* Reference Bar */}
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-rose-500/10 border border-rose-500/25 p-3 text-xs">
                <div className="flex items-center gap-2 text-rose-200">
                  <Icon name="shieldCheck" size={16} />
                  <span className="font-mono font-bold">{result.notice_reference}</span>
                  <span className="text-rose-300/60">· Ready to dispatch</span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => copyToClipboard(result.legal_notice_text, 'notice')}
                    className="inline-flex items-center gap-1 rounded-lg bg-rose-500/20 px-2.5 py-1 font-medium text-rose-200 hover:bg-rose-500/30 transition"
                  >
                    <Icon name={copiedNotice ? 'check' : 'copy'} size={14} />
                    <span>{copiedNotice ? 'Copied!' : 'Copy Notice'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={downloadNotice}
                    className="inline-flex items-center gap-1 rounded-lg bg-rose-500/20 px-2.5 py-1 font-medium text-rose-200 hover:bg-rose-500/30 transition"
                  >
                    <Icon name="download" size={14} />
                    <span>Download (.txt)</span>
                  </button>
                </div>
              </div>

              {/* Pre-Litigation Legal Notice Preview */}
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-subtle">
                    15-Day Pre-Litigation Statutory Legal Notice
                  </span>
                  <span className="text-[0.68rem] text-muted">Serve via Email or Speed Post</span>
                </div>
                <div className="max-h-64 overflow-y-auto rounded-xl border border-line bg-field/80 p-4 font-mono text-xs text-fg leading-relaxed whitespace-pre-wrap select-all">
                  {result.legal_notice_text}
                </div>
              </div>

              {/* NCH 1915 INGRAM Complaint */}
              <div className="rounded-xl border border-line bg-glass p-4">
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs text-cyan-300 uppercase tracking-wider">
                      National Consumer Helpline (NCH 1915) Summary
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(result.nch_grievance_draft, 'nch')}
                    className="inline-flex items-center gap-1 text-xs text-cyan-glow hover:underline"
                  >
                    <Icon name={copiedNch ? 'check' : 'copy'} size={13} />
                    <span>{copiedNch ? 'Copied' : 'Copy NCH Draft'}</span>
                  </button>
                </div>
                <div className="rounded-lg bg-field/60 p-3 font-mono text-xs text-muted leading-relaxed whitespace-pre-wrap">
                  {result.nch_grievance_draft}
                </div>
              </div>

              {/* Action Portal Links */}
              <div className="grid gap-3 sm:grid-cols-3">
                <a
                  href={result.portal_links.edaakhil_url}
                  target="_blank"
                  rel="noreferrer"
                  className="glass hover:bg-glass-hover flex items-center justify-between rounded-xl p-3 text-xs text-fg transition"
                >
                  <div className="flex items-center gap-2">
                    <Icon name="externalLink" size={15} className="text-rose-400" />
                    <span className="font-medium">e-Daakhil Portal</span>
                  </div>
                  <span className="text-[0.68rem] text-subtle">edaakhil.nic.in</span>
                </a>

                <a
                  href={result.portal_links.nch_helpline_url}
                  target="_blank"
                  rel="noreferrer"
                  className="glass hover:bg-glass-hover flex items-center justify-between rounded-xl p-3 text-xs text-fg transition"
                >
                  <div className="flex items-center gap-2">
                    <Icon name="globe" size={15} className="text-cyan-glow" />
                    <span className="font-medium">NCH Helpline</span>
                  </div>
                  <span className="text-[0.68rem] text-subtle">Online Grievance</span>
                </a>

                <a
                  href={`tel:${result.portal_links.nch_toll_free_number}`}
                  className="glass hover:bg-glass-hover flex items-center justify-between rounded-xl p-3 text-xs text-fg transition"
                >
                  <div className="flex items-center gap-2">
                    <Icon name="zap" size={15} className="text-amber-400" />
                    <span className="font-medium">Call NCH 1915</span>
                  </div>
                  <span className="text-[0.68rem] text-subtle">Toll Free</span>
                </a>
              </div>

              <div className="pt-2 flex justify-between items-center">
                <button
                  type="button"
                  onClick={() => setResult(null)}
                  className="text-xs text-subtle hover:text-fg underline transition"
                >
                  ← Edit Information &amp; Regenerate
                </button>
                <Button variant="secondary" size="md" onClick={onClose}>
                  Done
                </Button>
              </div>
            </div>
          )}
        </GlassCard>
      </motion.div>
    </div>
  )
}

