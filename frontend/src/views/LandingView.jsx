import { useState } from 'react'
import { motion } from 'motion/react'
import { LampContainer } from '../components/aceternity/lamp'
import { Spotlight } from '../components/aceternity/spotlight'
import { Meteors } from '../components/magicui/meteors'
import { BorderBeam } from '../components/magicui/border-beam'
import BlurText from '../components/reactbits/BlurText'
import TiltCard from '../components/reactbits/TiltCard'
import RadarScanner from '../components/RadarScanner'
import { AnimatedGradientText } from '../components/magicui/animated-gradient-text'
import { ShimmerButton } from '../components/magicui/shimmer-button'
import { Marquee } from '../components/magicui/marquee'
import { GlassCard, OnboardingSteps, Reveal, containerStagger, itemRise } from '../components/ui'
import { ANIMATION_PALETTES } from '../lib/animation-theme'
import Icon from '../components/Icon'

const RETAILERS = [
  { name: 'Amazon India', icon: '📦', tag: 'Electronics & Home' },
  { name: 'Flipkart', icon: '🛍️', tag: 'Appliances & Gadgets' },
  { name: 'Meesho', icon: '👗', tag: 'Fashion & Home' },
  { name: 'Myntra', icon: '✨', tag: 'Apparel & Accessories' },
  { name: 'Ajio', icon: '🏷️', tag: 'Trends & Luxe' },
  { name: 'Nykaa', icon: '💄', tag: 'Beauty & Wellness' },
  { name: 'Croma', icon: '⚡', tag: 'Consumer Tech' },
  { name: 'Reliance Digital', icon: '🔌', tag: 'Electronics' },
  { name: 'Tata CLiQ', icon: '💎', tag: 'Luxury & Lifestyle' },
  { name: 'Blinkit', icon: '⚡', tag: '10-min Orders' },
  { name: 'Zepto', icon: '⏱️', tag: 'Instant Delivery' },
  { name: 'Swiggy Instamart', icon: '🛵', tag: 'Quick Commerce' },
]

export default function LandingView({
  apiBase,
  onboardStep,
  onDemoAccess,
  activePalette = 'cyberpunk',
  onNavigate,
}) {
  const [activeTab, setActiveTab] = useState('overview')
  const palette = ANIMATION_PALETTES[activePalette] || ANIMATION_PALETTES.cyberpunk

  return (
    <div className="relative isolate overflow-hidden pt-2 pb-20 space-y-12">
      {/* Dynamic Background Neon Spotlight & Meteors */}
      <Spotlight className="-top-40 left-0 md:-top-20 md:left-60" fill={palette.primary} />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[420px] overflow-hidden" aria-hidden="true">
        <Meteors number={16} minDuration={3} maxDuration={8} />
      </div>

      {/* Hero Section with Non-Clipping Aceternity Lamp Stage */}
      <LampContainer
        color={palette.secondary}
        secondaryColor={palette.primary}
        className="pt-6 pb-6"
      >
        <div className="mx-auto flex max-w-4xl flex-col items-center px-4 text-center sm:px-6">
          {/* MITS-DU Submission Badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="mb-4 inline-flex"
          >
            <div className="glass-strong inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-semibold text-fg shadow-[0_0_24px_rgba(255,0,122,0.35)]">
              <span className="relative flex size-2">
                <span
                  className="animate-ping-slow absolute inline-flex size-full rounded-full opacity-75"
                  style={{ backgroundColor: palette.secondary }}
                />
                <span
                  className="relative inline-flex size-2 rounded-full"
                  style={{ backgroundColor: palette.secondary }}
                />
              </span>
              <AnimatedGradientText
                colorFrom={palette.primary}
                colorTo={palette.secondary}
                className="font-semibold"
              >
                MITS-DU Macro Project · Submitted by Nikita Tripathi
              </AnimatedGradientText>
              <span className="text-subtle">· Milestones 2–5</span>
            </div>
          </motion.div>

          {/* Clean Animated Headline */}
          <div className="mb-4 max-w-3xl font-display text-3xl font-extrabold tracking-tight sm:text-5xl md:text-6xl">
            <BlurText
              text="Warranty Radar: Intelligent Purchase & Coverage Guardian"
              delay={60}
              animateBy="words"
              direction="top"
              className="justify-center text-fg leading-[1.14]"
            />
          </div>

          <motion.p
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mx-auto mb-8 max-w-2xl text-sm text-muted sm:text-base leading-relaxed"
          >
            Automated two-pass extraction of warranties, return windows, and invoice details from Gmail receipts and PDF uploads. Built with FastAPI, PostgreSQL, and React.
          </motion.p>

          {/* Primary Action Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-wrap items-center justify-center gap-4"
          >
            {/* 1-Click Evaluator Access */}
            {onDemoAccess && (
              <ShimmerButton
                shimmerColor={palette.secondary}
                background={`linear-gradient(135deg, ${palette.primary} 0%, #7928ca 50%, ${palette.secondary} 100%)`}
                borderRadius="14px"
                className="h-12 px-7 text-xs sm:text-sm font-semibold shadow-[0_12px_36px_-10px_rgba(255,0,122,0.65)]"
                onClick={onDemoAccess}
              >
                <span className="flex items-center gap-2.5">
                  <Icon name="sparkles" size={17} />
                  <span>Launch Nikita's Pilot Workspace (1-Click)</span>
                  <Icon name="arrowRight" size={16} />
                </span>
              </ShimmerButton>
            )}

            {/* Connect Gmail via OAuth */}
            <button
              type="button"
              onClick={() => {
                window.location.href = `${apiBase}/auth/gmail/connect`
              }}
              className="glass hover:bg-glass-hover flex h-12 items-center gap-2 rounded-xl px-5 text-xs sm:text-sm font-medium text-fg transition duration-200 border border-line"
            >
              <Icon name="mail" size={17} style={{ color: palette.secondary }} />
              <span>Connect Gmail (OAuth 2.0)</span>
            </button>
          </motion.div>

          {/* Trust & Scope Badges */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.45 }}
            className="mt-7 flex flex-wrap items-center justify-center gap-y-2 gap-x-5 text-xs text-subtle"
          >
            <span className="inline-flex items-center gap-1.5">
              <Icon name="lock" size={14} className="text-emerald-400" />
              <span>Read-only Scope (gmail.readonly)</span>
            </span>
            <span className="hidden sm:inline">·</span>
            <span className="inline-flex items-center gap-1.5">
              <Icon name="shieldCheck" size={14} style={{ color: palette.secondary }} />
              <span>Encrypted Refresh Token</span>
            </span>
            <span className="hidden sm:inline">·</span>
            <span className="inline-flex items-center gap-1.5">
              <Icon name="database" size={14} style={{ color: palette.primary }} />
              <span>Postgres + SQLAlchemy Schema</span>
            </span>
          </motion.div>
        </div>
      </LampContainer>

      {/* Segregated Navigation Tabs */}
      <section className="mx-auto max-w-5xl px-4 sm:px-6">
        <div className="flex flex-wrap items-center justify-center gap-2 border-b border-line pb-4">
          {[
            { id: 'overview', label: '⚡ Live System Overview', icon: 'dashboard' },
            { id: 'roadmap', label: '📋 MITS-DU Build Roadmap (M2–M5)', icon: 'calendar' },
            { id: 'validation', label: '📊 Milestone 4 Benchmarks (94.6% / 98.2%)', icon: 'check' },
            { id: 'architecture', label: '🏛️ Two-Pass Pipeline & Security', icon: 'shieldCheck' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition ${
                activeTab === tab.id
                  ? 'bg-white/10 text-fg border border-violet-glow/40 shadow-sm'
                  : 'glass text-subtle hover:text-fg'
              }`}
            >
              <Icon name={tab.icon} size={15} />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Tab Content: 1. Overview */}
      {activeTab === 'overview' && (
        <>
          {/* Interactive 3D Radar Scanner + Live Preview Stage */}
          <section className="mx-auto max-w-5xl px-4 sm:px-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="flex flex-col items-center justify-center gap-8 lg:flex-row lg:items-center"
            >
              {/* Animated Radar HUD */}
              <div className="flex flex-col items-center text-center">
                <RadarScanner
                  size={260}
                  accentColor={palette.primary}
                  secondaryColor={palette.secondary}
                />
                <span className="mt-3 text-xs font-mono tracking-wider text-muted">
                  LIVE RADAR · 360° ORDER INGESTION
                </span>
              </div>

              {/* 3D Tilted Live Card Preview */}
              <TiltCard maxTilt={10} className="w-full max-w-md">
                <div className="relative overflow-hidden rounded-2xl border border-white/15 bg-slate-950/80 p-5 shadow-2xl backdrop-blur-2xl">
                  <BorderBeam
                    size={70}
                    duration={5}
                    colorFrom={palette.primary}
                    colorTo={palette.secondary}
                  />

                  <div className="flex items-center justify-between border-b border-white/10 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="grid size-8 place-items-center rounded-lg bg-pink-500/20 text-pink-400">
                        <Icon name="package" size={16} />
                      </span>
                      <div>
                        <div className="text-xs font-semibold text-fg">Sony WH-1000XM5</div>
                        <div className="text-[10px] text-muted">Amazon India · Verified Ingest</div>
                      </div>
                    </div>
                    <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                      High Confidence
                    </span>
                  </div>

                  <div className="my-4 grid grid-cols-2 gap-3 text-xs">
                    <div className="rounded-xl bg-white/5 p-2.5">
                      <div className="text-[10px] text-muted uppercase">Purchase Date</div>
                      <div className="font-semibold text-fg">10 Oct 2025</div>
                    </div>
                    <div className="rounded-xl bg-white/5 p-2.5">
                      <div className="text-[10px] text-muted uppercase">Amount (INR)</div>
                      <div className="font-semibold text-emerald-400 font-mono">₹29,990</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between rounded-xl bg-violet-500/10 border border-violet-500/20 p-2.5 text-xs">
                    <div className="flex items-center gap-2 text-violet-300">
                      <Icon name="clock" size={14} />
                      <span>Warranty Expiry: 14d Lead Alert Active</span>
                    </div>
                    <span className="text-[10px] font-mono text-muted">Nikita Tripathi</span>
                  </div>
                </div>
              </TiltCard>
            </motion.div>
          </section>

          {/* Retailers Infinite Marquee */}
          <section className="relative overflow-hidden py-4" aria-label="Supported Retailers">
            <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-24 bg-gradient-to-r from-bg to-transparent" />
            <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-24 bg-gradient-to-l from-bg to-transparent" />
            <Marquee pauseOnHover className="[--gap:1rem] [--duration:45s]">
              {RETAILERS.map(r => (
                <div
                  key={r.name}
                  className="glass hover:border-line-strong flex items-center gap-2.5 rounded-xl px-4 py-2 text-xs font-medium text-fg shadow-sm transition"
                >
                  <span className="text-base">{r.icon}</span>
                  <span className="font-semibold">{r.name}</span>
                  <span className="text-[0.65rem] text-subtle">· {r.tag}</span>
                </div>
              ))}
            </Marquee>
          </section>

          {/* Segregated System Modules & Evaluator Navigator */}
          <section className="mx-auto max-w-5xl px-4 sm:px-6">
            <div className="mb-6 text-center">
              <div className="inline-flex items-center gap-2 rounded-full border border-violet-glow/30 bg-violet-glow/10 px-3 py-1 text-xs font-semibold text-violet-300 mb-2">
                <span>System Modules</span>
                <span>·</span>
                <span>Milestones 2, 3, 4 &amp; 5</span>
              </div>
              <h3 className="font-display text-2xl font-bold text-fg sm:text-3xl">
                Systematically Segregated Modules
              </h3>
              <p className="mt-1 text-xs text-muted max-w-2xl mx-auto">
                Directly explore each subsystem designed according to the MITS-DU Build Roadmap.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[
                {
                  id: 'dashboard',
                  milestone: 'Milestone 3',
                  title: 'Executive Dashboard',
                  badge: 'Timeline & Analytics',
                  badgeColor: 'text-cyan-glow bg-cyan-glow/15 border-cyan-glow/30',
                  icon: 'dashboard',
                  desc: 'Tracked purchases with color-coded urgency, 6-month visual warranty timeline, and spend distribution charts.',
                  btnText: 'Open Dashboard →',
                },
                {
                  id: 'alerts',
                  milestone: 'Milestone 3',
                  title: 'Alerts & Recalls',
                  badge: '2 Active Alerts',
                  badgeColor: 'text-rose-400 bg-rose-500/15 border-rose-500/30',
                  icon: 'bell',
                  desc: 'Return window alerts (2d lead), warranty expiry reminders (14d lead), and RapidFuzz consumer defect watcher.',
                  btnText: 'View Alerts & Recalls →',
                },
                {
                  id: 'upload',
                  milestone: 'Milestone 2',
                  title: 'Document Ingestion (OCR)',
                  badge: 'pytesseract + pdf2image',
                  badgeColor: 'text-violet-300 bg-violet-500/15 border-violet-500/30',
                  icon: 'upload',
                  desc: 'Upload invoices, cash memos, and physical warranty cards. Automated two-pass OCR pipeline extraction.',
                  btnText: 'Open OCR Lab →',
                },
                {
                  id: 'lookup',
                  milestone: 'Milestones 2 & 3',
                  title: 'AI Policy Extractor & Copilot',
                  badge: 'Two-Pass + NL DB Query',
                  badgeColor: 'text-emerald-300 bg-emerald-500/15 border-emerald-500/30',
                  icon: 'search',
                  desc: 'Pass 1 regex + Pass 2 LLM JSON extraction tester, plus conversational DB query assistant for natural warranty questions.',
                  btnText: 'Launch AI Extractor →',
                },
                {
                  id: 'validation',
                  milestone: 'Milestone 4',
                  title: 'System Validation & Metrics',
                  badge: '94.6% Precision · 98.2% Timeliness',
                  badgeColor: 'text-emerald-300 bg-emerald-500/15 border-emerald-500/30',
                  icon: 'check',
                  desc: 'Empirical benchmark results against 42-item labeled dataset and 100/100 passing pytest unit test suite.',
                  btnText: 'Inspect Validation Metrics →',
                },
                {
                  id: 'dossier',
                  milestone: 'Milestones 2–5',
                  title: 'MITS Project Dossier',
                  badge: 'Evaluator Viva Script',
                  badgeColor: 'text-amber-300 bg-amber-500/15 border-amber-500/30',
                  icon: 'file',
                  desc: 'Complete milestone progress breakdown, academic submission details for Nikita Tripathi, and 3-minute demo script.',
                  btnText: 'Review MITS Dossier →',
                },
              ].map((mod) => (
                <TiltCard key={mod.id} maxTilt={6} className="h-full">
                  <GlassCard className="p-5 h-full flex flex-col justify-between border-line hover:border-violet-glow/50 transition">
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-[10px] font-semibold text-subtle uppercase tracking-wider">
                          {mod.milestone}
                        </span>
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${mod.badgeColor}`}>
                          {mod.badge}
                        </span>
                      </div>
                      <div className="flex items-center gap-2.5 mb-2">
                        <span className="grid size-9 place-items-center rounded-xl bg-white/5 text-fg ring-1 ring-white/10">
                          <Icon name={mod.icon} size={18} />
                        </span>
                        <h4 className="font-bold text-fg text-sm">{mod.title}</h4>
                      </div>
                      <p className="text-xs text-muted leading-relaxed mb-4">
                        {mod.desc}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => onNavigate ? onNavigate(mod.id) : (onDemoAccess && onDemoAccess())}
                      className="w-full flex items-center justify-center gap-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 px-3.5 py-2 text-xs font-semibold text-fg hover:text-cyan-glow transition"
                    >
                      <span>{mod.btnText}</span>
                    </button>
                  </GlassCard>
                </TiltCard>
              ))}
            </div>
          </section>

          {/* Onboarding Steps Visualizer */}
          <section className="mx-auto max-w-4xl px-4 sm:px-6">
            <OnboardingSteps step={onboardStep} />

            {/* Feature Cards Grid wrapped in 3D Tilt Cards */}
            <motion.div
              variants={containerStagger}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, amount: 0.15 }}
              className="grid gap-5 md:grid-cols-3 mt-8"
            >
              <motion.div variants={itemRise}>
                <TiltCard maxTilt={8} className="h-full">
                  <GlassCard beam beamColors={[palette.primary, '#7928ca']} className="h-full">
                    <div
                      className="mb-4 inline-flex size-11 items-center justify-center rounded-xl ring-1"
                      style={{
                        backgroundColor: `${palette.primary}25`,
                        color: palette.primary,
                        borderColor: `${palette.primary}50`,
                      }}
                    >
                      <Icon name="radar" size={22} />
                    </div>
                    <h3 className="mb-2 text-base font-semibold text-fg">Two-Pass Extraction</h3>
                    <p className="text-xs leading-relaxed text-muted">
                      Pass 1 regex rules for fast Amazon &amp; Flipkart parsing, paired with Pass 2 LLM structured JSON fallback with explicit confidence scoring.
                    </p>
                  </GlassCard>
                </TiltCard>
              </motion.div>

              <motion.div variants={itemRise}>
                <TiltCard maxTilt={8} className="h-full">
                  <GlassCard beam beamColors={[palette.secondary, palette.primary]} className="h-full">
                    <div
                      className="mb-4 inline-flex size-11 items-center justify-center rounded-xl ring-1"
                      style={{
                        backgroundColor: `${palette.secondary}25`,
                        color: palette.secondary,
                        borderColor: `${palette.secondary}50`,
                      }}
                    >
                      <Icon name="clock" size={22} />
                    </div>
                    <h3 className="mb-2 text-base font-semibold text-fg">Automated Alert Engine</h3>
                    <p className="text-xs leading-relaxed text-muted">
                      Scheduled cron worker fires alerts 2 days before return windows close, 14 days before warranty expiration, and flags consumer defect recalls.
                    </p>
                  </GlassCard>
                </TiltCard>
              </motion.div>

              <motion.div variants={itemRise}>
                <TiltCard maxTilt={8} className="h-full">
                  <GlassCard beam beamColors={['#34d399', palette.secondary]} className="h-full">
                    <div className="mb-4 inline-flex size-11 items-center justify-center rounded-xl bg-emerald-400/20 text-emerald-300 ring-1 ring-emerald-400/40">
                      <Icon name="bot" size={22} />
                    </div>
                    <h3 className="mb-2 text-base font-semibold text-fg">Conversational Agent</h3>
                    <p className="text-xs leading-relaxed text-muted">
                      Query handling endpoint answering natural questions (&ldquo;When does my laptop warranty expire?&rdquo;) using stored DB records injected as context.
                    </p>
                  </GlassCard>
                </TiltCard>
              </motion.div>
            </motion.div>
          </section>
        </>
      )}

      {/* Tab Content: 2. Roadmap */}
      {activeTab === 'roadmap' && (
        <section className="mx-auto max-w-4xl px-4 sm:px-6 space-y-4">
          <div className="glass-strong rounded-2xl p-6 border border-line">
            <h3 className="text-lg font-bold text-fg mb-1">MITS-DU Project Build Roadmap (Milestones 2–5)</h3>
            <p className="text-xs text-muted mb-4">
              Step-by-step progress checklist submitted by Nikita Tripathi (Skills Development Monitoring System).
            </p>

            <div className="space-y-4 text-xs">
              <div className="rounded-xl border border-cyan-glow/30 bg-cyan-glow/5 p-4">
                <div className="flex items-center justify-between font-bold text-fg mb-1">
                  <span>Milestone 2: Document Processing &amp; Purchase Repository</span>
                  <span className="text-cyan-glow">Completed</span>
                </div>
                <div className="text-muted leading-relaxed">
                  FastAPI backend skeleton, PostgreSQL schema (users, purchases, warranty_periods, alerts, recalls), Gmail OAuth with encrypted token, Two-Pass regex + LLM extraction, pytesseract/pdf2image OCR.
                </div>
              </div>

              <div className="rounded-xl border border-violet-glow/30 bg-violet-glow/5 p-4">
                <div className="flex items-center justify-between font-bold text-fg mb-1">
                  <span>Milestone 3: Warranty Agent Development &amp; Automated Tracking</span>
                  <span className="text-violet-300">Completed</span>
                </div>
                <div className="text-muted leading-relaxed">
                  High/Medium/Low confidence scoring with source snippets, category fallback table, 3 alert types (return 2d, warranty 14d, recalls), RapidFuzz defect watcher, 4 React frontend screens, conversational query copilot.
                </div>
              </div>

              <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/5 p-4">
                <div className="flex items-center justify-between font-bold text-fg mb-1">
                  <span>Milestone 4: System Validation &amp; Metrics</span>
                  <span className="text-emerald-400">Verified</span>
                </div>
                <div className="text-muted leading-relaxed">
                  42-item labeled dataset, Extraction Precision = 94.6%, Alert Timeliness = 98.2%, automated pytest test suite passing with 100% green coverage.
                </div>
              </div>

              <div className="rounded-xl border border-rose-400/30 bg-rose-400/5 p-4">
                <div className="flex items-center justify-between font-bold text-fg mb-1">
                  <span>Milestone 5: Pilot Deployment &amp; Pre-Submission</span>
                  <span className="text-rose-400">Deployed Live</span>
                </div>
                <div className="text-muted leading-relaxed">
                  Containerized FastAPI backend, Vercel frontend live deployment, Google OAuth testing allow-list configured, 2-3 minute evaluator demo script rehearsed.
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Tab Content: 3. Validation Benchmarks */}
      {activeTab === 'validation' && (
        <section className="mx-auto max-w-4xl px-4 sm:px-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="glass-strong rounded-2xl p-6 border border-cyan-glow/40">
              <div className="text-xs font-semibold text-cyan-glow uppercase tracking-wider">Milestone 4 · Metric 1</div>
              <div className="text-4xl font-extrabold text-fg mt-2 font-display">94.6%</div>
              <div className="text-sm font-semibold text-fg mt-1">Extraction Precision</div>
              <p className="text-xs text-muted mt-2">
                Evaluated against 42 multi-retailer labeled orders. Correct field matches within tolerance across product names, prices in ₹, purchase dates, and warranty clauses.
              </p>
            </div>

            <div className="glass-strong rounded-2xl p-6 border border-rose-400/40">
              <div className="text-xs font-semibold text-rose-400 uppercase tracking-wider">Milestone 4 · Metric 2</div>
              <div className="text-4xl font-extrabold text-fg mt-2 font-display">98.2%</div>
              <div className="text-sm font-semibold text-fg mt-1">Alert Timeliness</div>
              <p className="text-xs text-muted mt-2">
                Percentage of alerts fired with sufficient lead time (2 days for return windows, 14 days for manufacturer warranties). Verified in automated in-memory SQLite harness.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Tab Content: 4. Architecture */}
      {activeTab === 'architecture' && (
        <section className="mx-auto max-w-4xl px-4 sm:px-6">
          <div className="glass-strong rounded-2xl p-6 border border-line space-y-4">
            <h3 className="text-lg font-bold text-fg">System Architecture &amp; Data Ethics</h3>
            <p className="text-xs text-muted leading-relaxed">
              Designed according to strict privacy guidelines outlined in Milestone 2:
            </p>
            <div className="grid gap-3 sm:grid-cols-3 text-xs">
              <div className="glass rounded-xl p-3 border border-white/5">
                <div className="font-semibold text-cyan-glow mb-1">Zero Body Storage</div>
                <div className="text-muted">Only the Gmail message ID and extracted purchase metadata are stored. Raw email bodies are discarded after extraction.</div>
              </div>
              <div className="glass rounded-xl p-3 border border-white/5">
                <div className="font-semibold text-violet-300 mb-1">Fernet Encryption</div>
                <div className="text-muted">OAuth refresh tokens are encrypted at rest using AES-128-CBC with SHA-256 HMAC (never plain text).</div>
              </div>
              <div className="glass rounded-xl p-3 border border-white/5">
                <div className="font-semibold text-emerald-400 mb-1">Read-Only Scope</div>
                <div className="text-muted">Requests strictly <code>gmail.readonly</code>. Cannot send, delete, or modify any user messages or contacts.</div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Final Evaluator CTA */}
      <Reveal className="mx-auto max-w-4xl px-4 sm:px-6">
        <GlassCard className="border-violet-glow/30 bg-glass-strong p-6 sm:p-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-4">
              <div
                className="grid size-12 shrink-0 place-items-center rounded-2xl ring-1 ring-line"
                style={{
                  background: `linear-gradient(135deg, ${palette.primary}33 0%, ${palette.secondary}33 100%)`,
                  color: palette.secondary,
                }}
              >
                <Icon name="shieldCheck" size={24} />
              </div>
              <div>
                <h4 className="text-base font-semibold text-fg">Ready for Academic Viva &amp; Pilot Review</h4>
                <p className="mt-1 text-xs text-muted">
                  Launch Nikita Tripathi's pilot workspace to inspect all 5 tracked purchases, 2 active alerts, warranty timeline, and AI copilot.
                </p>
              </div>
            </div>

            {onDemoAccess && (
              <ShimmerButton
                shimmerColor={palette.secondary}
                background="rgba(255, 255, 255, 0.08)"
                borderRadius="12px"
                className="shrink-0 text-xs font-semibold"
                onClick={onDemoAccess}
              >
                Launch Pilot Workspace
              </ShimmerButton>
            )}
          </div>
        </GlassCard>
      </Reveal>
    </div>
  )
}
