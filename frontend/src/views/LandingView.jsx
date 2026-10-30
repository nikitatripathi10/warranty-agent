import { useState } from 'react'
import { motion } from 'motion/react'
import { LampContainer } from '../components/aceternity/lamp'
import BlurText from '../components/reactbits/BlurText'
import TiltCard from '../components/reactbits/TiltCard'
import { Marquee } from '../components/magicui/marquee'
import { GlassCard, OnboardingSteps, Reveal, containerStagger, itemRise } from '../components/ui'
import { ANIMATION_PALETTES } from '../lib/animation-theme'
import Icon from '../components/Icon'

const RETAILERS = [
  { name: 'Amazon India', icon: '📦', tag: 'Electronics & Home' },
  { name: 'Flipkart', icon: '🛍️', tag: 'Appliances & Gadgets' },
  { name: 'Croma', icon: '⚡', tag: 'Consumer Tech' },
  { name: 'Reliance Digital', icon: '🔌', tag: 'Electronics' },
  { name: 'Myntra', icon: '✨', tag: 'Apparel & Accessories' },
  { name: 'Ajio', icon: '🏷️', tag: 'Fashion & Lifestyle' },
  { name: 'Nykaa', icon: '💄', tag: 'Personal Care' },
  { name: 'Tata CLiQ', icon: '💎', tag: 'Electronics & Luxe' },
  { name: 'Blinkit', icon: '⚡', tag: 'Quick Commerce' },
  { name: 'Zepto', icon: '⏱️', tag: 'Instant Delivery' },
  { name: 'Swiggy Instamart', icon: '🛵', tag: 'Daily Essentials' },
  { name: 'Meesho', icon: '👗', tag: 'Marketplace' },
]

export default function LandingView({
  apiBase,
  onboardStep,
  activePalette = 'cyberpunk',
}) {
  const [activeTab, setActiveTab] = useState('features')
  const palette = ANIMATION_PALETTES[activePalette] || ANIMATION_PALETTES.cyberpunk

  const handleConnectGmail = () => {
    window.location.href = `${apiBase}/auth/gmail/connect`
  }

  return (
    <div className="relative isolate overflow-hidden pt-2 pb-20 space-y-12">
      {/* Hero Section with Soft Ambient Lamp Stage */}
      <LampContainer
        color={palette.secondary}
        secondaryColor={palette.primary}
        className="pt-6 pb-4"
      >
        <div className="mx-auto flex max-w-3xl flex-col items-center px-4 text-center sm:px-6">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="mb-4 inline-flex"
          >
            <div className="glass inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-medium text-muted">
              <span
                className="inline-flex size-2 rounded-full"
                style={{ backgroundColor: palette.secondary }}
              />
              <span>Automated Purchase, Return Window &amp; Warranty Tracker</span>
            </div>
          </motion.div>

          <div className="mb-4 max-w-3xl font-display text-3xl font-bold tracking-tight sm:text-5xl">
            <BlurText
              text="Keep every invoice, return window, and warranty in one calm place."
              delay={50}
              animateBy="words"
              direction="top"
              className="justify-center text-fg leading-[1.16]"
            />
          </div>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="mx-auto mb-8 max-w-2xl text-sm text-muted sm:text-base leading-relaxed"
          >
            Connect your Gmail or upload PDF invoices and warranty slips. Warranty Radar extracts purchase dates, coverage terms, and return deadlines automatically and reminds you before coverage expires.
          </motion.p>

          {/* Primary Action: Real Google OAuth */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.25 }}
            className="flex flex-wrap items-center justify-center gap-4"
          >
            <button
              type="button"
              onClick={handleConnectGmail}
              className="flex h-12 items-center gap-2.5 rounded-xl border border-violet-glow/45 bg-violet-glow/25 px-6 text-sm font-semibold text-fg shadow-md transition duration-200 hover:bg-violet-glow/35"
            >
              <Icon name="mail" size={17} />
              <span>Connect Gmail with Google</span>
              <Icon name="arrowRight" size={15} />
            </button>
          </motion.div>

          {/* Trust & Privacy Badges */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.35 }}
            className="mt-7 flex flex-wrap items-center justify-center gap-y-2 gap-x-5 text-xs text-subtle"
          >
            <span className="inline-flex items-center gap-1.5">
              <Icon name="lock" size={14} className="text-emerald-400/90" />
              <span>Read-only access (gmail.readonly)</span>
            </span>
            <span className="hidden sm:inline">·</span>
            <span className="inline-flex items-center gap-1.5">
              <Icon name="shieldCheck" size={14} className="text-muted" />
              <span>Encrypted OAuth tokens</span>
            </span>
            <span className="hidden sm:inline">·</span>
            <span className="inline-flex items-center gap-1.5">
              <Icon name="database" size={14} className="text-muted" />
              <span>Raw email bodies are never stored</span>
            </span>
          </motion.div>
        </div>
      </LampContainer>

      {/* Supported Retailers Marquee */}
      <section className="relative overflow-hidden py-3" aria-label="Supported Retailers">
        <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-24 bg-gradient-to-r from-bg to-transparent" />
        <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-24 bg-gradient-to-l from-bg to-transparent" />
        <Marquee pauseOnHover className="[--gap:1rem] [--duration:50s]">
          {RETAILERS.map(r => (
            <div
              key={r.name}
              className="glass flex items-center gap-2.5 rounded-xl px-4 py-2 text-xs font-medium text-fg transition hover:border-line-strong"
            >
              <span className="text-base">{r.icon}</span>
              <span className="font-semibold">{r.name}</span>
              <span className="text-[0.65rem] text-subtle">· {r.tag}</span>
            </div>
          ))}
        </Marquee>
      </section>

      {/* Segregated Section Navigation */}
      <section className="mx-auto max-w-4xl px-4 sm:px-6">
        <div className="flex flex-wrap items-center justify-center gap-2 border-b border-line pb-4">
          {[
            { id: 'features', label: 'Capabilities', icon: 'dashboard' },
            { id: 'workflow', label: 'How It Works', icon: 'clock' },
            { id: 'privacy', label: 'Privacy & Security', icon: 'shieldCheck' },
          ].map(tab => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition ${
                activeTab === tab.id
                  ? 'border border-violet-glow/35 bg-violet-glow/15 text-fg'
                  : 'glass text-subtle hover:text-fg'
              }`}
            >
              <Icon name={tab.icon} size={15} />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Tab 1: Capabilities */}
      {activeTab === 'features' && (
        <section className="mx-auto max-w-4xl px-4 sm:px-6">
          <motion.div
            variants={containerStagger}
            initial="hidden"
            animate="show"
            className="grid gap-5 md:grid-cols-3"
          >
            <motion.div variants={itemRise}>
              <TiltCard maxTilt={5} className="h-full">
                <GlassCard className="h-full p-5" intensity={0.06}>
                  <div className="mb-4 inline-flex size-10 items-center justify-center rounded-xl bg-violet-glow/15 text-violet-300 ring-1 ring-line">
                    <Icon name="radar" size={20} />
                  </div>
                  <h3 className="mb-2 text-base font-semibold text-fg">Receipt &amp; Invoice Parsing</h3>
                  <p className="text-xs leading-relaxed text-muted">
                    Automatically identifies product names, brands, order totals, purchase dates, and warranty durations from order confirmation emails and uploaded PDFs or images.
                  </p>
                </GlassCard>
              </TiltCard>
            </motion.div>

            <motion.div variants={itemRise}>
              <TiltCard maxTilt={5} className="h-full">
                <GlassCard className="h-full p-5" intensity={0.06}>
                  <div className="mb-4 inline-flex size-10 items-center justify-center rounded-xl bg-cyan-glow/15 text-cyan-300 ring-1 ring-line">
                    <Icon name="clock" size={20} />
                  </div>
                  <h3 className="mb-2 text-base font-semibold text-fg">Timely Expiry Reminders</h3>
                  <p className="text-xs leading-relaxed text-muted">
                    Schedules alerts ahead of return window deadlines and warranty expirations, and checks your products against published recall notices.
                  </p>
                </GlassCard>
              </TiltCard>
            </motion.div>

            <motion.div variants={itemRise}>
              <TiltCard maxTilt={5} className="h-full">
                <GlassCard className="h-full p-5" intensity={0.06}>
                  <div className="mb-4 inline-flex size-10 items-center justify-center rounded-xl bg-emerald-400/15 text-emerald-300 ring-1 ring-line">
                    <Icon name="bot" size={20} />
                  </div>
                  <h3 className="mb-2 text-base font-semibold text-fg">Natural-Language Assistant</h3>
                  <p className="text-xs leading-relaxed text-muted">
                    Ask questions about your own purchases—such as which items can still be returned or when coverage ends—answered directly from your saved records.
                  </p>
                </GlassCard>
              </TiltCard>
            </motion.div>
          </motion.div>
        </section>
      )}

      {/* Tab 2: How It Works */}
      {activeTab === 'workflow' && (
        <section className="mx-auto max-w-4xl px-4 sm:px-6 space-y-6">
          <OnboardingSteps step={onboardStep} />
          <div className="grid gap-4 sm:grid-cols-3 text-xs">
            <GlassCard className="p-4" intensity={0.05}>
              <div className="font-semibold text-fg mb-1">1. Connect or Upload</div>
              <p className="text-muted leading-relaxed">
                Sign in with Google to scan order confirmation emails, or upload PDF bills and physical warranty slips directly.
              </p>
            </GlassCard>
            <GlassCard className="p-4" intensity={0.05}>
              <div className="font-semibold text-fg mb-1">2. Review &amp; Edit</div>
              <p className="text-muted leading-relaxed">
                Each extracted record includes a confidence rating and source snippet. Edit any field or assign items to household members.
              </p>
            </GlassCard>
            <GlassCard className="p-4" intensity={0.05}>
              <div className="font-semibold text-fg mb-1">3. Stay Notified</div>
              <p className="text-muted leading-relaxed">
                Track active coverage on a visual timeline and get notified before return windows or manufacturer warranties expire.
              </p>
            </GlassCard>
          </div>
        </section>
      )}

      {/* Tab 3: Privacy & Security */}
      {activeTab === 'privacy' && (
        <section className="mx-auto max-w-4xl px-4 sm:px-6">
          <GlassCard className="p-6 space-y-4" intensity={0.06}>
            <h3 className="text-base font-semibold text-fg">Privacy &amp; Data Handling</h3>
            <div className="grid gap-4 sm:grid-cols-3 text-xs">
              <div className="rounded-xl border border-line bg-glass p-4">
                <div className="font-semibold text-fg mb-1">Minimal Gmail Scope</div>
                <p className="text-muted leading-relaxed">
                  Requests only <code className="font-mono text-fg">gmail.readonly</code> to search for order and invoice receipts. Cannot send, modify, or delete emails.
                </p>
              </div>
              <div className="rounded-xl border border-line bg-glass p-4">
                <div className="font-semibold text-fg mb-1">No Raw Email Retention</div>
                <p className="text-muted leading-relaxed">
                  Only the Gmail message ID and structured purchase metadata are saved. Full email bodies are discarded immediately after extraction.
                </p>
              </div>
              <div className="rounded-xl border border-line bg-glass p-4">
                <div className="font-semibold text-fg mb-1">Encrypted Credentials</div>
                <p className="text-muted leading-relaxed">
                  OAuth refresh tokens are encrypted at rest with symmetric Fernet encryption before being stored in PostgreSQL.
                </p>
              </div>
            </div>
          </GlassCard>
        </section>
      )}

      {/* Bottom CTA */}
      <Reveal className="mx-auto max-w-4xl px-4 sm:px-6">
        <GlassCard className="p-6 sm:p-7" intensity={0.06}>
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-4">
              <div className="grid size-11 shrink-0 place-items-center rounded-2xl bg-violet-glow/15 text-violet-300 ring-1 ring-line">
                <Icon name="shieldCheck" size={22} />
              </div>
              <div>
                <h4 className="text-base font-semibold text-fg">Ready to organize your warranties?</h4>
                <p className="mt-1 text-xs text-muted">
                  Connect your Gmail account to scan your purchase receipts and track active coverage.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleConnectGmail}
              className="shrink-0 rounded-xl border border-violet-glow/40 bg-violet-glow/20 px-5 py-2.5 text-xs font-semibold text-fg transition hover:bg-violet-glow/30"
            >
              Connect Gmail
            </button>
          </div>
        </GlassCard>
      </Reveal>
    </div>
  )
}
