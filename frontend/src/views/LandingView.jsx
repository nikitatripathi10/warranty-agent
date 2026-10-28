import { motion } from 'motion/react'
import { Spotlight } from '../components/aceternity/spotlight'
import { Meteors } from '../components/magicui/meteors'
import BlurText from '../components/reactbits/BlurText'
import { AnimatedGradientText } from '../components/magicui/animated-gradient-text'
import { ShimmerButton } from '../components/magicui/shimmer-button'
import { Marquee } from '../components/magicui/marquee'
import { GlassCard, OnboardingSteps, Reveal, containerStagger, itemRise } from '../components/ui'
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

export default function LandingView({ apiBase, onboardStep, onDemoAccess }) {
  return (
    <div className="relative isolate overflow-hidden pt-6 pb-20">
      {/* Aceternity Spotlight effect */}
      <Spotlight className="-top-40 left-0 md:-top-20 md:left-60" fill="#a78bfa" />

      {/* Meteors in hero section */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[480px] overflow-hidden" aria-hidden="true">
        <Meteors number={16} minDuration={3} maxDuration={8} />
      </div>

      {/* Hero Section */}
      <section className="relative z-10 mx-auto flex max-w-4xl flex-col items-center px-4 text-center sm:px-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="mb-5 inline-flex"
        >
          <div className="glass-strong inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-medium text-fg shadow-[0_0_20px_rgba(139,92,246,0.35)]">
            <span className="relative flex size-2">
              <span className="animate-ping-slow absolute inline-flex size-full rounded-full bg-cyan-glow opacity-75" />
              <span className="relative inline-flex size-2 rounded-full bg-cyan-glow" />
            </span>
            <AnimatedGradientText colorFrom="#a78bfa" colorTo="#22d3ee" className="font-semibold">
              🇮🇳 AI Purchase &amp; Warranty Radar
            </AnimatedGradientText>
            <span className="text-subtle">· v0.4</span>
          </div>
        </motion.div>

        {/* Animated Headline using BlurText */}
        <div className="mb-4 max-w-3xl font-display text-4xl font-extrabold tracking-tight sm:text-5xl md:text-6xl">
          <BlurText
            text="Never lose another warranty or miss a return window."
            delay={80}
            animateBy="words"
            direction="top"
            className="justify-center text-fg leading-[1.12]"
          />
        </div>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mx-auto mb-8 max-w-2xl text-base text-muted sm:text-lg"
        >
          Automatically extract warranties, return periods, and invoice details from your
          Gmail receipts &amp; PDF uploads. Intelligent notifications keep thousands of rupees protected.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex flex-wrap items-center justify-center gap-4"
        >
          <ShimmerButton
            shimmerColor="#22d3ee"
            background="linear-gradient(135deg, #7c3aed 0%, #3b82f6 50%, #06b6d4 100%)"
            borderRadius="14px"
            className="h-12 px-7 text-sm font-semibold shadow-[0_12px_36px_-10px_rgba(124,58,237,0.7)]"
            onClick={() => {
              window.location.href = `${apiBase}/auth/gmail/connect`
            }}
          >
            <span className="flex items-center gap-2.5">
              <Icon name="mail" size={18} />
              <span>Connect with Google</span>
              <Icon name="arrowRight" size={16} />
            </span>
          </ShimmerButton>

          {onDemoAccess && (
            <button
              type="button"
              onClick={onDemoAccess}
              className="glass hover:bg-glass-hover flex h-12 items-center gap-2 rounded-xl px-5 text-sm font-medium text-fg transition duration-200"
            >
              <Icon name="sparkles" size={17} className="text-cyan-glow" />
              <span>Explore Demo Workspace</span>
            </button>
          )}
        </motion.div>

        {/* Trust Badges */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.45 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-y-2 gap-x-5 text-xs text-subtle"
        >
          <span className="inline-flex items-center gap-1.5">
            <Icon name="lock" size={14} className="text-emerald-400" />
            <span>Read-only Gmail scope</span>
          </span>
          <span className="hidden sm:inline">·</span>
          <span className="inline-flex items-center gap-1.5">
            <Icon name="shieldCheck" size={14} className="text-cyan-glow" />
            <span>Zero email body storage</span>
          </span>
          <span className="hidden sm:inline">·</span>
          <span className="inline-flex items-center gap-1.5">
            <Icon name="key" size={14} className="text-violet-glow" />
            <span>Revocable anytime</span>
          </span>
        </motion.div>
      </section>

      {/* Retailers Infinite Marquee */}
      <section className="relative mt-14 overflow-hidden py-4" aria-label="Supported Retailers">
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

      {/* Onboarding steps visualizer */}
      <section className="mx-auto mt-14 max-w-4xl px-4 sm:px-6">
        <OnboardingSteps step={onboardStep} />

        {/* Feature Cards Grid */}
        <motion.div
          variants={containerStagger}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.15 }}
          className="grid gap-5 md:grid-cols-3"
        >
          <motion.div variants={itemRise}>
            <GlassCard beam beamColors={['#8b5cf6', '#4f7cff']} className="h-full">
              <div className="mb-4 inline-flex size-11 items-center justify-center rounded-xl bg-violet-glow/20 text-violet-300 ring-1 ring-violet-glow/40">
                <Icon name="radar" size={22} />
              </div>
              <h3 className="mb-2 text-base font-semibold text-fg">AI Invoice Extraction</h3>
              <p className="text-xs leading-relaxed text-muted">
                Recognizes purchase dates, retailer identifiers, prices in ₹, and warranty policy clauses
                from order confirmations and PDF invoices with high precision.
              </p>
            </GlassCard>
          </motion.div>

          <motion.div variants={itemRise}>
            <GlassCard beam beamColors={['#22d3ee', '#8b5cf6']} className="h-full">
              <div className="mb-4 inline-flex size-11 items-center justify-center rounded-xl bg-cyan-glow/20 text-cyan-glow ring-1 ring-cyan-glow/40">
                <Icon name="clock" size={22} />
              </div>
              <h3 className="mb-2 text-base font-semibold text-fg">Proactive Countdown Alerts</h3>
              <p className="text-xs leading-relaxed text-muted">
                Interactive timeline and smart alert engine notify you 30, 7, and 1 day before your
                return windows snap shut and factory warranties expire.
              </p>
            </GlassCard>
          </motion.div>

          <motion.div variants={itemRise}>
            <GlassCard beam beamColors={['#34d399', '#22d3ee']} className="h-full">
              <div className="mb-4 inline-flex size-11 items-center justify-center rounded-xl bg-emerald-400/20 text-emerald-300 ring-1 ring-emerald-400/40">
                <Icon name="bot" size={22} />
              </div>
              <h3 className="mb-2 text-base font-semibold text-fg">Natural Language Warranty Agent</h3>
              <p className="text-xs leading-relaxed text-muted">
                Ask questions like &ldquo;Which items can I still return?&rdquo; or &ldquo;How much total coverage
                do I have?&rdquo; and receive instant, structured answers.
              </p>
            </GlassCard>
          </motion.div>
        </motion.div>
      </section>

      {/* Privacy & Security banner */}
      <Reveal className="mx-auto mt-14 max-w-4xl px-4 sm:px-6">
        <GlassCard className="border-violet-glow/30 bg-glass-strong p-6 sm:p-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-4">
              <div className="grid size-12 shrink-0 place-items-center rounded-2xl bg-linear-to-br from-violet-glow/30 to-cyan-glow/20 text-cyan-glow ring-1 ring-line">
                <Icon name="lock" size={24} />
              </div>
              <div>
                <h4 className="text-base font-semibold text-fg">Bank-Grade Privacy &amp; Data Ethics</h4>
                <p className="mt-1 text-xs text-muted">
                  We only inspect email sender, subject, and purchase metadata. Your personal correspondence,
                  contacts, and inbox contents are never touched or sold.
                </p>
              </div>
            </div>
            <ShimmerButton
              shimmerColor="#22d3ee"
              background="rgba(255, 255, 255, 0.08)"
              borderRadius="12px"
              className="shrink-0 text-xs font-semibold"
              onClick={() => {
                window.location.href = `${apiBase}/auth/gmail/connect`
              }}
            >
              Get Started Now
            </ShimmerButton>
          </div>
        </GlassCard>
      </Reveal>
    </div>
  )
}

