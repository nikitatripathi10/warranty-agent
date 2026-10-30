import { useState, useRef } from 'react'
import { motion } from 'motion/react'
import { LampContainer } from '../components/aceternity/lamp'
import { Marquee } from '../components/magicui/marquee'
import {
  GlassCard,
  Button,
  Spinner,
  Textarea,
  Notice,
  UserChip,
  OnboardingSteps,
} from '../components/ui'
import ResultGrid from '../components/ResultGrid'
import { ANIMATION_PALETTES } from '../lib/animation-theme'
import Icon from '../components/Icon'

const RETAILERS = [
  'Amazon India',
  'Flipkart',
  'Croma',
  'Reliance Digital',
  'Myntra',
  'Ajio',
  'Nykaa',
  'Tata CLiQ',
  'Blinkit',
  'Zepto',
  'Swiggy Instamart',
  'Meesho',
]

export default function LandingView({
  apiBase,
  isConnected,
  userEmail,
  onDisconnect,
  onNavigate,
  onboardStep,
  activePalette = 'cyberpunk',
  // Scan Inbox props
  fetchLoading,
  fetchResult,
  fetchError,
  onScanInbox,
  // Upload Document props
  uploadFile,
  setUploadFile,
  uploadLoading,
  uploadProgress,
  uploadResult,
  uploadError,
  onUpload,
  // Quick Lookup props
  testText,
  setTestText,
  testLoading,
  testResult,
  testError,
  onTestExtraction,
  // Dashboard summary count
  purchasesCount = 0,
  alertsCount = 0,
}) {
  const [dragover, setDragover] = useState(false)
  const fileInputRef = useRef(null)
  const palette = ANIMATION_PALETTES[activePalette] || ANIMATION_PALETTES.cyberpunk

  const handleConnectGmail = () => {
    window.location.href = `${apiBase}/auth/gmail/connect`
  }

  return (
    <div className="relative isolate overflow-hidden pt-2 pb-16 space-y-8">
      {/* ── Hero Section ─────────────────────────────────────────────────── */}
      <LampContainer
        color={palette.secondary}
        secondaryColor={palette.primary}
        className="pt-6 pb-2"
      >
        <div className="mx-auto flex max-w-3xl flex-col items-center px-4 text-center sm:px-6">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="mb-4 inline-flex"
          >
            <div className="glass inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-semibold text-fg shadow-sm">
              <span>🇮🇳</span>
              <span>Designed for Indian Shoppers</span>
            </div>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.05 }}
            className="mb-4 max-w-3xl font-display text-3xl font-extrabold tracking-tight text-fg sm:text-5xl leading-[1.15]"
          >
            Your <span className="text-aurora">warranty</span> and{' '}
            <span className="text-aurora">return window</span> tracker
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.12 }}
            className="mx-auto mb-6 max-w-2xl text-sm text-muted sm:text-base leading-relaxed"
          >
            Automatically scans your Gmail for purchase confirmations, extracts warranty terms and
            return deadlines, and reminds you before your coverage runs out.
          </motion.p>

          {/* Retailer Tags */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="flex flex-wrap justify-center gap-2 max-w-2xl"
          >
            {RETAILERS.map(r => (
              <span
                key={r}
                className="glass rounded-full px-3 py-1 text-xs font-medium text-muted transition hover:border-line-strong hover:text-fg"
              >
                {r}
              </span>
            ))}
          </motion.div>
        </div>
      </LampContainer>

      {/* ── Onboarding Steps ─────────────────────────────────────────────── */}
      <div className="mx-auto max-w-2xl px-4">
        <OnboardingSteps step={isConnected ? Math.max(1, onboardStep) : 0} />
      </div>

      {/* ── All-in-One Workspace Stack (Matches Original Layout & Screenshots) ── */}
      <div className="mx-auto max-w-2xl px-4 space-y-6">
        {/* 1. Connect Your Gmail / Gmail Account Card */}
        <GlassCard beam beamColors={['#6366f1', '#38bdf8']} className="p-6 sm:p-7">
          <div className="mb-5 flex items-start justify-between gap-3">
            <div className="flex items-center gap-3.5">
              <div className="grid size-11 shrink-0 place-items-center rounded-xl border border-indigo-400/30 bg-indigo-500/20 text-lg shadow-sm">
                ✉️
              </div>
              <div>
                <h2 className="text-lg font-bold text-fg">
                  {isConnected ? 'Gmail Account' : 'Connect Your Gmail'}
                </h2>
                <p className="text-xs text-muted">
                  {isConnected
                    ? 'Connected and ready to scan'
                    : 'Grant read-only access to detect order confirmations'}
                </p>
              </div>
            </div>

            {isConnected && onNavigate && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onNavigate('dashboard')}
              >
                <Icon name="dashboard" size={14} />
                <span>Dashboard ({purchasesCount})</span>
              </Button>
            )}
          </div>

          {!isConnected ? (
            <div className="space-y-4">
              <div className="space-y-2.5">
                {[
                  {
                    icon: '🔒',
                    bold: 'Read-only access',
                    text: ' — we never send or delete emails',
                  },
                  {
                    icon: '🛡️',
                    bold: 'Encrypted credentials',
                    text: ' — tokens stored with AES encryption',
                  },
                  {
                    icon: '📋',
                    bold: 'Metadata only',
                    text: ' — raw email content is never saved',
                  },
                ].map(item => (
                  <div
                    key={item.bold}
                    className="glass flex items-center gap-3 rounded-xl px-4 py-3 text-xs sm:text-sm text-muted"
                  >
                    <span className="text-base">{item.icon}</span>
                    <span>
                      <strong className="font-semibold text-fg">{item.bold}</strong>
                      {item.text}
                    </span>
                  </div>
                ))}
              </div>

              <a
                id="btn-connect-gmail"
                href={`${apiBase}/auth/gmail/connect`}
                className="flex w-full items-center justify-center gap-2.5 rounded-xl border border-indigo-400/40 bg-linear-to-r from-indigo-500 to-violet-600 px-6 py-3.5 text-sm font-semibold text-white shadow-[0_8px_24px_-6px_rgba(99,102,241,0.55)] transition hover:from-indigo-400 hover:to-violet-500"
              >
                <svg width="18" height="18" viewBox="0 0 48 48" style={{ flexShrink: 0 }}>
                  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
                  <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
                  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
                </svg>
                <span>Connect with Google</span>
              </a>
            </div>
          ) : (
            <div className="space-y-4">
              <Notice tone="success">Your Gmail account is connected.</Notice>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <UserChip email={userEmail} />
                <div className="flex items-center gap-2">
                  {alertsCount > 0 && onNavigate && (
                    <Button variant="secondary" size="sm" onClick={() => onNavigate('alerts')}>
                      <Icon name="bell" size={14} className="text-amber-300" />
                      <span>{alertsCount} Alerts</span>
                    </Button>
                  )}
                  <Button
                    id="btn-disconnect"
                    variant="danger"
                    size="sm"
                    onClick={onDisconnect}
                  >
                    Remove Account
                  </Button>
                </div>
              </div>
            </div>
          )}
        </GlassCard>

        {/* 2. Scan Inbox Card */}
        <GlassCard className="p-6 sm:p-7">
          <div className="mb-5 flex items-center gap-3.5">
            <div className="grid size-11 shrink-0 place-items-center rounded-xl border border-cyan-400/30 bg-cyan-500/15 text-lg shadow-sm">
              🔍
            </div>
            <div>
              <h2 className="text-lg font-bold text-fg">Scan Inbox</h2>
              <p className="text-xs text-muted">
                Identify and import purchase records from your recent emails
              </p>
            </div>
          </div>

          <Button
            id="btn-fetch-emails"
            variant="primary"
            size="lg"
            full
            onClick={isConnected ? onScanInbox : handleConnectGmail}
            disabled={fetchLoading}
          >
            {fetchLoading ? (
              <>
                <Spinner size={16} />
                <span>Scanning your inbox…</span>
              </>
            ) : (
              <span>Scan for Purchases</span>
            )}
          </Button>

          {!isConnected && (
            <p className="mt-2.5 text-center text-xs text-subtle">
              Clicking above will connect your Google account first to enable inbox scanning.
            </p>
          )}

          {fetchError && (
            <Notice tone="error" className="mt-4">
              {fetchError}
            </Notice>
          )}

          {fetchResult && (
            <div className="mt-5 space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="glass rounded-xl p-3.5 text-center">
                  <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">
                    Emails reviewed
                  </div>
                  <div className="mt-1 font-display text-xl font-bold text-fg">
                    {fetchResult.emails_scanned}
                  </div>
                </div>
                <div className="glass rounded-xl p-3.5 text-center">
                  <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">
                    Records saved
                  </div>
                  <div className="mt-1 font-display text-xl font-bold text-emerald-400">
                    {fetchResult.purchases_created}
                  </div>
                </div>
                <div className="glass rounded-xl p-3.5 text-center">
                  <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-subtle">
                    Not processed
                  </div>
                  <div className="mt-1 font-display text-xl font-bold text-amber-300">
                    {fetchResult.purchases_failed}
                  </div>
                </div>
              </div>

              {onNavigate && (
                <Button
                  variant="secondary"
                  size="sm"
                  full
                  onClick={() => onNavigate('dashboard')}
                >
                  <span>View Imported Purchases in Dashboard →</span>
                </Button>
              )}
            </div>
          )}
        </GlassCard>

        {/* 3. Upload a Document Card */}
        <GlassCard className="p-6 sm:p-7">
          <div className="mb-5 flex items-center gap-3.5">
            <div className="grid size-11 shrink-0 place-items-center rounded-xl border border-indigo-400/30 bg-indigo-500/15 text-lg shadow-sm">
              📄
            </div>
            <div>
              <h2 className="text-lg font-bold text-fg">Upload a Document</h2>
              <p className="text-xs text-muted">
                Submit an invoice, warranty card, or purchase receipt for extraction
              </p>
            </div>
          </div>

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
            className={`relative mb-4 cursor-pointer rounded-2xl border-2 border-dashed px-6 py-9 text-center transition-all ${
              dragover
                ? 'border-cyan-glow bg-cyan-glow/10 shadow-[0_0_30px_rgba(56,189,248,0.25)]'
                : 'border-line hover:border-indigo-400/60 hover:bg-glass-hover'
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

            <div className="mx-auto mb-3 text-3xl">
              {uploadFile ? '📎' : '📁'}
            </div>

            {uploadFile ? (
              <div>
                <div className="text-sm font-semibold text-cyan-glow break-all">
                  {uploadFile.name}
                </div>
                <div className="mt-1 text-xs text-subtle">
                  {(uploadFile.size / 1024 / 1024).toFixed(2)} MB · Click or drag to replace
                </div>
              </div>
            ) : (
              <div>
                <div className="text-sm font-semibold text-fg">
                  Drag and drop a file here, or{' '}
                  <span className="text-cyan-glow underline">browse</span>
                </div>
                <div className="mt-1 text-xs text-subtle">
                  PDF, JPEG, PNG, WEBP, TIFF — up to 20 MB
                </div>
              </div>
            )}
          </div>

          {uploadLoading && uploadProgress > 0 && (
            <div className="mb-4 h-2 overflow-hidden rounded-full bg-line">
              <motion.div
                className="h-full bg-linear-to-r from-indigo-500 to-sky-400 transition-all"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          )}

          <Button
            id="btn-upload"
            variant="accent"
            size="lg"
            full
            onClick={isConnected ? onUpload : handleConnectGmail}
            disabled={!uploadFile || uploadLoading}
          >
            {uploadLoading ? (
              <>
                <Spinner size={16} />
                <span>Analysing document…</span>
              </>
            ) : (
              <span>Analyse &amp; Save</span>
            )}
          </Button>

          {!isConnected && uploadFile && (
            <p className="mt-2.5 text-center text-xs text-subtle">
              Connect your Google account first to save extracted documents to your profile.
            </p>
          )}

          {uploadError && (
            <Notice tone="error" className="mt-4">
              {uploadError}
            </Notice>
          )}

          {uploadResult && (
            <div className="mt-5 space-y-4">
              <Notice tone="success">Purchase record saved successfully.</Notice>
              <ResultGrid result={uploadResult.extraction} ocrUsed={uploadResult.ocr_used} />
            </div>
          )}
        </GlassCard>

        {/* 4. Quick Lookup Card */}
        <GlassCard className="p-6 sm:p-7">
          <div className="mb-5 flex items-center gap-3.5">
            <div className="grid size-11 shrink-0 place-items-center rounded-xl border border-cyan-400/30 bg-cyan-500/15 text-lg shadow-sm">
              🔎
            </div>
            <div>
              <h2 className="text-lg font-bold text-fg">Quick Lookup</h2>
              <p className="text-xs text-muted">
                Paste the text from an order confirmation email or invoice to extract warranty details
              </p>
            </div>
          </div>

          <Textarea
            id="extraction-test-input"
            rows={7}
            value={testText}
            onChange={e => setTestText(e.target.value)}
            placeholder={`Paste your order confirmation text here, for example:\n\nDear Customer,\nThank you for your order from Amazon.in!\nOrder #402-1234567-8901234 — Placed on 15 January 2025\nItem: Sony WH-1000XM5 Wireless Headphones\nOrder Total: ₹24,990.00\nThis product carries a 1 year manufacturer warranty.\nEligible for return within 10 days of delivery.`}
            className="mb-4 font-mono text-xs leading-relaxed"
          />

          <Button
            id="btn-test-extraction"
            variant="secondary"
            size="lg"
            full
            onClick={onTestExtraction}
            disabled={!testText.trim() || testLoading}
          >
            {testLoading ? (
              <>
                <Spinner size={16} />
                <span>Extracting details…</span>
              </>
            ) : (
              <span>Extract Warranty Details</span>
            )}
          </Button>

          {testError && (
            <Notice tone="error" className="mt-4">
              {testError}
            </Notice>
          )}

          {testResult && (
            <div className="mt-5">
              <ResultGrid result={testResult} />
            </div>
          )}
        </GlassCard>
      </div>

      {/* ── Marquee Ticker ───────────────────────────────────────────────── */}
      <section className="relative overflow-hidden py-2" aria-label="Supported Retailers">
        <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-20 bg-gradient-to-r from-bg to-transparent" />
        <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-20 bg-gradient-to-l from-bg to-transparent" />
        <Marquee pauseOnHover className="[--gap:0.85rem] [--duration:45s]">
          {RETAILERS.map(name => (
            <div
              key={name}
              className="glass flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold text-fg"
            >
              <span className="size-1.5 rounded-full bg-cyan-glow" />
              <span>{name}</span>
            </div>
          ))}
        </Marquee>
      </section>
    </div>
  )
}
