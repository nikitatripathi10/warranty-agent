import { useState, useRef } from 'react'
import { motion } from 'motion/react'
import { GlassCard, Button, Spinner } from '../components/ui'
import ResultGrid from '../components/ResultGrid'
import Icon from '../components/Icon'

export default function UploadView({
  uploadFile,
  setUploadFile,
  uploadLoading,
  uploadProgress,
  uploadResult,
  uploadError,
  onUpload,
}) {
  const [dragover, setDragover] = useState(false)
  const fileInputRef = useRef(null)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-bold tracking-tight text-fg sm:text-3xl">
          Upload Invoice or Warranty Slip
        </h2>
        <p className="mt-1 text-xs text-muted">
          Upload any PDF bill, cash memo, or photo of a physical warranty card to index it automatically.
        </p>
      </div>

      <GlassCard beam beamColors={['#8b5cf6', '#22d3ee']} className="p-6 sm:p-8">
        {/* Drag & drop upload zone */}
        <div
          onDragOver={e => {
            e.preventDefault()
            setDragover(true)
          }}
          onDragLeave={() => setDragover(false)}
          onDrop={e => {
            e.preventDefault()
            setDragover(false)
            const f = e.dataTransfer.files?.[0]
            if (f) setUploadFile(f)
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`relative cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
            dragover
              ? 'border-cyan-glow bg-cyan-glow/10 shadow-[0_0_30px_rgba(34,211,238,0.3)]'
              : 'border-line hover:border-violet-glow/60 hover:bg-glass-hover'
          }`}
        >
          <input
            id="upload-file-input"
            ref={fileInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.webp,.tiff"
            onChange={e => setUploadFile(e.target.files?.[0])}
            style={{ display: 'none' }}
          />

          <div className="mx-auto mb-3 grid size-14 place-items-center rounded-2xl bg-violet-glow/20 text-cyan-glow ring-1 ring-line">
            <Icon name={uploadFile ? 'paperclip' : 'upload'} size={28} />
          </div>

          {uploadFile ? (
            <div>
              <div className="font-semibold text-fg">{uploadFile.name}</div>
              <div className="mt-1 text-xs text-subtle">
                {(uploadFile.size / 1024 / 1024).toFixed(2)} MB · Click or drag to replace
              </div>
            </div>
          ) : (
            <div>
              <div className="text-sm font-semibold text-fg">
                Drag and drop your file here, or <span className="text-cyan-glow underline">browse</span>
              </div>
              <div className="mt-1 text-xs text-subtle">
                Supported: PDF, JPEG, PNG, WEBP, TIFF (max 20 MB)
              </div>
            </div>
          )}
        </div>

        {/* Progress bar */}
        {uploadLoading && uploadProgress > 0 && (
          <div className="mt-4 overflow-hidden rounded-full bg-line h-2">
            <motion.div
              className="h-full bg-linear-to-r from-violet-glow to-cyan-glow transition-all"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        )}

        {/* Action Button */}
        <div className="mt-6 flex justify-end">
          <Button
            id="btn-upload"
            variant="primary"
            size="md"
            onClick={onUpload}
            disabled={!uploadFile || uploadLoading}
          >
            {uploadLoading ? (
              <>
                <Spinner size={16} />
                <span>Processing Document…</span>
              </>
            ) : (
              <>
                <Icon name="sparkles" size={16} />
                <span>Analyse &amp; Save Record</span>
              </>
            )}
          </Button>
        </div>

        {uploadError && (
          <div className="mt-4 rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-xs text-rose-200">
            {uploadError}
          </div>
        )}

        {uploadResult && (
          <div className="mt-6 border-t border-line pt-6">
            <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-emerald-400">
              ✓ Successfully Extracted &amp; Saved
            </div>
            <ResultGrid result={uploadResult.extraction} ocrUsed={uploadResult.ocr_used} />
          </div>
        )}
      </GlassCard>
    </div>
  )
}

