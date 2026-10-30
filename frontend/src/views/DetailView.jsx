import { motion } from 'motion/react'
import { GlassCard, Button, Field, ConfidenceBadge, UrgencyChip, Spinner } from '../components/ui'
import { fmt, fmtDate, fmtPrice, daysUntil } from '../lib/format'
import Icon from '../components/Icon'

export default function DetailView({
  purchase,
  onBack,
  editMode,
  setEditMode,
  editForm,
  setEditForm,
  editLoading,
  editError,
  onSaveEdit,
  onDeletePurchase,
  agentQuestion,
  setAgentQuestion,
  agentAnswer,
  agentLoading,
  onAgentQuery,
}) {
  const wp = purchase.warranty_period
  const returnDays = wp?.return_window_end_date ? daysUntil(wp.return_window_end_date) : null
  const warrantyDays = wp?.warranty_end_date ? daysUntil(wp.warranty_end_date) : null

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <button
          type="button"
          onClick={onBack}
          className="glass hover:bg-glass-hover inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-medium text-fg transition"
        >
          <Icon name="arrowLeft" size={15} />
          <span>Back to Dashboard</span>
        </button>
      </div>

      {/* Main Detail Card */}
      <GlassCard beam beamColors={['#8b5cf6', '#22d3ee']} className="p-6 sm:p-8">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between border-b border-line pb-6">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <span className="grid size-7 place-items-center rounded-lg bg-glass text-sm">
                {purchase.source_type === 'email' ? '📧' : '📄'}
              </span>
              <span className="text-xs font-semibold uppercase tracking-wider text-muted">
                {fmt(purchase.retailer || purchase.brand, '')}
              </span>
            </div>
            <h2 className="font-display text-2xl font-bold text-fg sm:text-3xl">
              {fmt(purchase.product_name, '')}
            </h2>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-subtle">
              {purchase.purchase_date && <span>Purchased on {fmtDate(purchase.purchase_date)}</span>}
              {purchase.family_member && <span>Assigned to: {purchase.family_member}</span>}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <ConfidenceBadge confidence={wp?.confidence_score || 'low'} />
            {wp?.is_estimated && (
              <span className="rounded bg-violet-glow/15 px-2 py-0.5 text-xs font-medium text-violet-300 ring-1 ring-violet-glow/30">
                Estimated
              </span>
            )}
          </div>
        </div>

        {!editMode ? (
          <div>
            {/* Metadata Grid */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="glass rounded-xl p-3.5">
                <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">Amount Paid</div>
                <div className="mt-1 text-lg font-bold text-cyan-glow">{fmtPrice(purchase.price)}</div>
              </div>

              <div className="glass rounded-xl p-3.5">
                <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">Purchase Date</div>
                <div className="mt-1 text-sm font-semibold text-fg">{fmtDate(purchase.purchase_date)}</div>
              </div>

              <div className="glass rounded-xl p-3.5">
                <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">Warranty Expiration</div>
                <div className="mt-1 flex items-center justify-between gap-1">
                  <span className="text-sm font-semibold text-fg">{fmtDate(wp?.warranty_end_date)}</span>
                  {warrantyDays !== null && (
                    <UrgencyChip days={warrantyDays} label={`${Math.abs(warrantyDays)}d`} />
                  )}
                </div>
              </div>

              <div className="glass rounded-xl p-3.5">
                <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">Return Window</div>
                <div className="mt-1 flex items-center justify-between gap-1">
                  <span className="text-sm font-semibold text-fg">{fmtDate(wp?.return_window_end_date)}</span>
                  {returnDays !== null && (
                    <UrgencyChip days={returnDays} label={`${Math.abs(returnDays)}d`} />
                  )}
                </div>
              </div>
            </div>

            {/* Extracted Evidence Snippet */}
            {wp?.source_snippet && (
              <div className="mt-6 rounded-xl border border-line bg-glass p-4">
                <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-subtle">
                  Extraction Source Evidence
                </div>
                <p className="font-mono text-xs text-muted leading-relaxed whitespace-pre-wrap">
                  &ldquo;{wp.source_snippet}&rdquo;
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Button
                variant="secondary"
                size="md"
                onClick={() => {
                  setEditMode(true)
                  setEditForm({
                    ...purchase,
                    warranty_end_date: wp?.warranty_end_date || '',
                    return_window_end_date: wp?.return_window_end_date || '',
                  })
                }}
              >
                <Icon name="pencil" size={15} />
                <span>Edit Record</span>
              </Button>

              <Button
                variant="danger"
                size="md"
                onClick={() => onDeletePurchase(purchase.id)}
              >
                <Icon name="trash" size={15} />
                <span>Delete</span>
              </Button>
            </div>
          </div>
        ) : (
          /* Inline Edit Form */
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                id="edit-product-name"
                label="Product Name"
                value={editForm.product_name || ''}
                onChange={v => setEditForm(f => ({ ...f, product_name: v }))}
              />
              <Field
                id="edit-brand"
                label="Brand"
                value={editForm.brand || ''}
                onChange={v => setEditForm(f => ({ ...f, brand: v }))}
              />
              <Field
                id="edit-retailer"
                label="Retailer"
                value={editForm.retailer || ''}
                onChange={v => setEditForm(f => ({ ...f, retailer: v }))}
              />
              <Field
                id="edit-purchase-date"
                label="Purchase Date"
                type="date"
                value={editForm.purchase_date || ''}
                onChange={v => setEditForm(f => ({ ...f, purchase_date: v }))}
              />
              <Field
                id="edit-price"
                label="Price (₹)"
                type="number"
                value={editForm.price || ''}
                onChange={v => setEditForm(f => ({ ...f, price: v }))}
              />
              <Field
                id="edit-family-member"
                label="Household Member"
                value={editForm.family_member || ''}
                onChange={v => setEditForm(f => ({ ...f, family_member: v }))}
              />
              <Field
                id="edit-warranty-date"
                label="Warranty Expiration"
                type="date"
                value={editForm.warranty_end_date || ''}
                onChange={v => setEditForm(f => ({ ...f, warranty_end_date: v }))}
              />
              <Field
                id="edit-return-date"
                label="Return Window Expiration"
                type="date"
                value={editForm.return_window_end_date || ''}
                onChange={v => setEditForm(f => ({ ...f, return_window_end_date: v }))}
              />
            </div>

            {editError && (
              <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-xs text-rose-200">
                {editError}
              </div>
            )}

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Button
                variant="primary"
                size="md"
                onClick={onSaveEdit}
                disabled={editLoading}
              >
                {editLoading ? <Spinner size={15} /> : 'Save Changes'}
              </Button>
              <Button
                variant="secondary"
                size="md"
                onClick={() => setEditMode(false)}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </GlassCard>

      {/* ── AI Warranty Agent Query Box ──────────────────────────────────── */}
      <GlassCard className="p-6">
        <div className="mb-4 flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-violet-glow/20 text-violet-300 ring-1 ring-line">
            <Icon name="bot" size={20} />
          </div>
          <div>
            <h3 className="text-base font-semibold text-fg">Ask AI Warranty Agent</h3>
            <p className="text-xs text-muted">
              Ask questions regarding {purchase.product_name || 'this item'} or your overall warranty coverage.
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <input
            id="agent-question-input"
            type="text"
            value={agentQuestion}
            onChange={e => setAgentQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && onAgentQuery()}
            placeholder={`e.g. "Can I still return my ${purchase.product_name?.split(' ')[0] || 'order'}?"`}
            className="flex-1 rounded-xl border border-line bg-field px-4 py-2.5 text-sm text-fg placeholder:text-subtle outline-none backdrop-blur-md transition hover:border-line-strong focus:border-violet-glow/70 focus:ring-4 focus:ring-violet-glow/15"
          />
          <Button
            variant="primary"
            size="md"
            onClick={onAgentQuery}
            disabled={agentLoading || !agentQuestion.trim()}
          >
            {agentLoading ? <Spinner size={15} /> : <Icon name="send" size={16} />}
          </Button>
        </div>

        {agentAnswer && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 flex items-start gap-3 rounded-xl border border-violet-glow/30 bg-violet-glow/10 p-4 text-sm text-fg"
          >
            <span className="text-lg">🤖</span>
            <div className="leading-relaxed">{agentAnswer}</div>
          </motion.div>
        )}
      </GlassCard>
    </div>
  )
}
