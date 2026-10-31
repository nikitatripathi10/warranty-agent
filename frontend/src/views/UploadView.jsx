import { useState, useRef } from 'react'
import { motion } from 'motion/react'
import { GlassCard, Button, Spinner, Notice, Field, Textarea, Select } from '../components/ui'
import ResultGrid from '../components/ResultGrid'
import Icon from '../components/Icon'

export default function UploadView({
  uploadFile,
  setUploadFile,
  additionalUploadFile,
  setAdditionalUploadFile,
  additionalWarrantyMonths = '',
  setAdditionalWarrantyMonths,
  additionalWarrantyNotes = '',
  setAdditionalWarrantyNotes,
  selectedUploadPurchaseId = '',
  setSelectedUploadPurchaseId,
  purchases = [],
  uploadLoading,
  uploadProgress,
  uploadResult,
  uploadError,
  onUpload,
}) {
  const [dragoverStd, setDragoverStd] = useState(false)
  const [dragoverAdd, setDragoverAdd] = useState(false)
  const stdFileInputRef = useRef(null)
  const addFileInputRef = useRef(null)

  const hasManualAdditional = Boolean(
    String(additionalWarrantyMonths || '').trim() || String(additionalWarrantyNotes || '').trim()
  )
  const canSubmit = Boolean(
    uploadFile || additionalUploadFile || (selectedUploadPurchaseId && hasManualAdditional)
  )

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-bold tracking-tight text-fg sm:text-3xl">
          Upload Invoice or Warranty Slip
        </h2>
        <p className="mt-1 text-xs text-muted">
          Upload your Manufacturer / Standard Warranty document and/or Additional / Extended Warranty document, or manually enter additional warranty details.
        </p>
      </div>

      <GlassCard beam beamColors={['#8b5cf6', '#22d3ee']} className="p-6 sm:p-8 space-y-6">
        {/* ── Dual Separate Document Upload Areas ─────────────────────────── */}
        <div className="grid gap-5 md:grid-cols-2">
          {/* 1. Manufacturer / Standard Warranty Document */}
          <div className="flex flex-col justify-between rounded-2xl border border-line bg-glass/40 p-4">
            <div className="mb-3 flex items-start justify-between gap-2">
              <div>
                <span className="inline-block rounded-full bg-violet-glow/20 px-2.5 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-violet-300 ring-1 ring-violet-glow/30">
                  Document 1 · Standard
                </span>
                <h3 className="mt-1.5 text-sm font-bold text-fg">
                  Manufacturer / Standard Warranty Document
                </h3>
                <p className="mt-0.5 text-xs text-muted">
                  Primary purchase invoice, retail bill, or standard manufacturer warranty slip
                </p>
              </div>
              {uploadFile && (
                <button
                  type="button"
                  onClick={() => setUploadFile(null)}
                  title="Remove file"
                  className="rounded-lg px-2 py-1 text-xs text-subtle hover:bg-rose-500/15 hover:text-rose-300 transition"
                >
                  Clear ×
                </button>
              )}
            </div>

            <div
              onDragOver={e => {
                e.preventDefault()
                setDragoverStd(true)
              }}
              onDragLeave={() => setDragoverStd(false)}
              onDrop={e => {
                e.preventDefault()
                setDragoverStd(false)
                const f = e.dataTransfer.files?.[0]
                if (f) setUploadFile(f)
              }}
              onClick={() => stdFileInputRef.current?.click()}
              className={`relative cursor-pointer rounded-2xl border-2 border-dashed p-6 text-center transition-all ${
                dragoverStd
                  ? 'border-cyan-glow bg-cyan-glow/10 shadow-[0_0_30px_rgba(34,211,238,0.3)]'
                  : 'border-line hover:border-violet-glow/60 hover:bg-glass-hover'
              }`}
            >
              <input
                id="upload-file-input"
                ref={stdFileInputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp,.tiff"
                onChange={e => setUploadFile(e.target.files?.[0] || null)}
                style={{ display: 'none' }}
              />

              <div className="mx-auto mb-3 grid size-12 place-items-center rounded-2xl bg-violet-glow/20 text-cyan-glow ring-1 ring-line">
                <Icon name={uploadFile ? 'paperclip' : 'upload'} size={24} />
              </div>

              {uploadFile ? (
                <div>
                  <div className="font-semibold text-sm text-cyan-glow break-all">{uploadFile.name}</div>
                  <div className="mt-1 text-xs text-subtle">
                    {(uploadFile.size / 1024 / 1024).toFixed(2)} MB · Click or drag to replace
                  </div>
                </div>
              ) : (
                <div>
                  <div className="text-xs sm:text-sm font-semibold text-fg">
                    Drop Manufacturer Warranty file, or <span className="text-cyan-glow underline">browse</span>
                  </div>
                  <div className="mt-1 text-[0.7rem] text-subtle">
                    PDF, JPEG, PNG, WEBP, TIFF (max 20 MB)
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 2. Additional / Extended Warranty Document */}
          <div className="flex flex-col justify-between rounded-2xl border border-line bg-glass/40 p-4">
            <div className="mb-3 flex items-start justify-between gap-2">
              <div>
                <span className="inline-block rounded-full bg-cyan-glow/20 px-2.5 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-cyan-300 ring-1 ring-cyan-glow/30">
                  Document 2 · Extended
                </span>
                <h3 className="mt-1.5 text-sm font-bold text-fg">
                  Additional / Extended Warranty Document
                </h3>
                <p className="mt-0.5 text-xs text-muted">
                  Extended warranty certificate, protection plan, or AMC document (if available)
                </p>
              </div>
              {additionalUploadFile && (
                <button
                  type="button"
                  onClick={() => setAdditionalUploadFile?.(null)}
                  title="Remove file"
                  className="rounded-lg px-2 py-1 text-xs text-subtle hover:bg-rose-500/15 hover:text-rose-300 transition"
                >
                  Clear ×
                </button>
              )}
            </div>

            <div
              onDragOver={e => {
                e.preventDefault()
                setDragoverAdd(true)
              }}
              onDragLeave={() => setDragoverAdd(false)}
              onDrop={e => {
                e.preventDefault()
                setDragoverAdd(false)
                const f = e.dataTransfer.files?.[0]
                if (f) setAdditionalUploadFile?.(f)
              }}
              onClick={() => addFileInputRef.current?.click()}
              className={`relative cursor-pointer rounded-2xl border-2 border-dashed p-6 text-center transition-all ${
                dragoverAdd
                  ? 'border-cyan-glow bg-cyan-glow/10 shadow-[0_0_30px_rgba(34,211,238,0.3)]'
                  : 'border-line hover:border-cyan-glow/60 hover:bg-glass-hover'
              }`}
            >
              <input
                id="upload-additional-file-input"
                ref={addFileInputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp,.tiff"
                onChange={e => setAdditionalUploadFile?.(e.target.files?.[0] || null)}
                style={{ display: 'none' }}
              />

              <div className="mx-auto mb-3 grid size-12 place-items-center rounded-2xl bg-cyan-glow/15 text-cyan-glow ring-1 ring-line">
                <Icon name={additionalUploadFile ? 'paperclip' : 'shieldCheck'} size={24} />
              </div>

              {additionalUploadFile ? (
                <div>
                  <div className="font-semibold text-sm text-cyan-glow break-all">
                    {additionalUploadFile.name}
                  </div>
                  <div className="mt-1 text-xs text-subtle">
                    {(additionalUploadFile.size / 1024 / 1024).toFixed(2)} MB · Click or drag to replace
                  </div>
                </div>
              ) : (
                <div>
                  <div className="text-xs sm:text-sm font-semibold text-fg">
                    Drop Additional Warranty file, or <span className="text-cyan-glow underline">browse</span>
                  </div>
                  <div className="mt-1 text-[0.7rem] text-subtle">
                    Upload together with Document 1 or on its own
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Manual Entry Option for Additional Warranty ─────────────────── */}
        <div className="rounded-2xl border border-line bg-glass/50 p-5 space-y-4">
          <div className="flex items-start gap-3">
            <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-violet-glow/20 text-cyan-glow ring-1 ring-line">
              <Icon name="pencil" size={17} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-fg">
                Manual Entry for Additional / Extended Warranty
              </h3>
              <p className="text-xs text-muted">
                Don&apos;t have an additional warranty document? Type your additional warranty details below to save and associate them with your product.
              </p>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              id="manual-additional-months"
              label="Additional Warranty Duration (Months)"
              type="number"
              min="1"
              max="120"
              placeholder="e.g. 12 or 24"
              value={additionalWarrantyMonths}
              onChange={v => setAdditionalWarrantyMonths?.(v)}
            />

            <div className="block">
              <span className="mb-1.5 block text-xs font-medium tracking-wide text-muted uppercase">
                Associate with Product
              </span>
              <Select
                value={selectedUploadPurchaseId}
                onChange={e => setSelectedUploadPurchaseId?.(e.target.value)}
                wrapClassName="w-full"
                className="w-full py-2.5"
              >
                <option value="">Auto-detect product from uploaded document(s)</option>
                {purchases.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.product_name} ({p.retailer || p.brand})
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div>
            <label
              htmlFor="manual-additional-notes"
              className="mb-1.5 block text-xs font-medium tracking-wide text-muted uppercase"
            >
              Additional Warranty Details / Coverage Notes
            </label>
            <Textarea
              id="manual-additional-notes"
              rows={3}
              value={additionalWarrantyNotes}
              onChange={e => setAdditionalWarrantyNotes?.(e.target.value)}
              placeholder="Write your additional/extended warranty details here (e.g., '1 Year Extended Warranty by OnsiteGo / AppleCare+, Policy #EXT-9021, covers accidental & liquid damage')…"
              className="text-xs leading-relaxed"
            />
          </div>
        </div>

        {/* Progress bar */}
        {uploadLoading && uploadProgress > 0 && (
          <div className="overflow-hidden rounded-full bg-line h-2">
            <motion.div
              className="h-full bg-linear-to-r from-violet-glow to-cyan-glow transition-all"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        )}

        {/* Action Button */}
        <div>
          <Button
            id="btn-upload"
            variant="accent"
            size="lg"
            full
            onClick={onUpload}
            disabled={!canSubmit || uploadLoading}
          >
            {uploadLoading ? (
              <>
                <Spinner size={16} />
                <span>Analysing &amp; saving warranty info…</span>
              </>
            ) : (
              <span>Analyse &amp; Save</span>
            )}
          </Button>
        </div>

        {uploadError && (
          <Notice tone="error">
            {uploadError}
          </Notice>
        )}

        {uploadResult && (
          <div className="space-y-4">
            <Notice tone="success">Purchase and warranty information saved successfully.</Notice>
            <ResultGrid result={uploadResult.extraction} ocrUsed={uploadResult.ocr_used} />
          </div>
        )}
      </GlassCard>
    </div>
  )
}

