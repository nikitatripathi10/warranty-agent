import { forwardRef } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import SpotlightCard from './reactbits/SpotlightCard'
import { BorderBeam } from './magicui/border-beam'
import { cn } from '../lib/utils'
import { useThemeValue } from '../lib/theme-context'
import Icon from './Icon'

/* ─────────────────────────── Motion presets ─────────────────────────── */
export const spring = { type: 'spring', stiffness: 380, damping: 24 }

export const containerStagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
}
export const itemRise = {
  hidden: { opacity: 0, y: 18, filter: 'blur(6px)' },
  show: { opacity: 1, y: 0, filter: 'blur(0px)', transition: { type: 'spring', stiffness: 220, damping: 26 } },
}

/** Scroll-triggered reveal (fade + rise + de-blur). */
export function Reveal({ children, delay = 0, y = 22, className, as = 'div', once = true, ...rest }) {
  const Comp = motion[as] || motion.div
  return (
    <Comp
      initial={{ opacity: 0, y, filter: 'blur(8px)' }}
      whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      viewport={{ once, amount: 0.15 }}
      transition={{ duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
      {...rest}
    >
      {children}
    </Comp>
  )
}

/* ─────────────────────────── Glass card ─────────────────────────── */
/**
 * Translucent glass surface built on React Bits' SpotlightCard: a cursor-following
 * spotlight + glowing edge, with backdrop blur. Optional Magic UI BorderBeam.
 */
export function GlassCard({
  children,
  className,
  style,
  beam = false,
  beamColors = ['#8b5cf6', '#22d3ee'],
  spotlight = 'var(--c-spot)',
  intensity = 0.14,
  size = 280,
  interactive = false,
  ...rest
}) {
  const theme = useThemeValue()
  return (
    <SpotlightCard
      theme={theme}
      spotlightColor={spotlight}
      intensity={intensity}
      spotlightSize={size}
      borderGlow={0.7}
      className={cn(
        'p-5 sm:p-6 rounded-2xl',
        interactive && 'cursor-pointer transition-[transform,box-shadow] duration-300 hover:-translate-y-1 active:translate-y-0 active:scale-[0.99] hover:shadow-[0_20px_60px_-20px_rgba(139,92,246,0.45)]',
        className
      )}
      style={{
        '--spotlight-card-surface': 'var(--c-glass)',
        '--spotlight-card-border': 'var(--c-border)',
        '--spotlight-card-shadow': 'var(--c-shadow)',
        WebkitBackdropFilter: 'blur(18px) saturate(150%)',
        backdropFilter: 'blur(18px) saturate(150%)',
        ...style,
      }}
      {...rest}
    >
      {beam && (
        <BorderBeam size={140} duration={9} colorFrom={beamColors[0]} colorTo={beamColors[1]} borderWidth={1.5} />
      )}
      {children}
    </SpotlightCard>
  )
}

/* ─────────────────────────── Buttons ─────────────────────────── */
const buttonBase =
  'relative inline-flex select-none items-center justify-center gap-2 rounded-xl font-medium whitespace-nowrap transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2'
const buttonSizes = {
  sm: 'px-3.5 py-2 text-[0.8rem]',
  md: 'px-5 py-2.5 text-sm',
  lg: 'px-7 py-3.5 text-base',
}
const buttonVariants = {
  primary:
    'text-white bg-linear-to-r from-violet-glow via-electric to-cyan-glow bg-[length:200%_100%] hover:bg-[position:100%_0] shadow-[0_8px_30px_-8px_rgba(99,102,241,0.7)] hover:shadow-[0_10px_40px_-6px_rgba(34,211,238,0.55)] transition-[background-position,box-shadow] duration-500',
  secondary: 'text-fg glass hover:bg-glass-hover hover:border-line-strong',
  ghost: 'text-muted hover:text-fg hover:bg-glass-hover',
  danger:
    'text-rose-300 light:text-rose-700 bg-rose-500/10 border border-rose-400/25 hover:bg-rose-500/20 hover:border-rose-400/50',
  accent:
    'text-white bg-linear-to-r from-cyan-500 to-electric shadow-[0_8px_30px_-8px_rgba(34,211,238,0.6)] hover:shadow-[0_10px_40px_-6px_rgba(34,211,238,0.8)]',
}

export const Button = forwardRef(function Button(
  { variant = 'primary', size = 'md', className, children, disabled, full, ...props },
  ref
) {
  return (
    <motion.button
      ref={ref}
      type="button"
      disabled={disabled}
      whileHover={disabled ? undefined : { scale: 1.03, y: -1 }}
      whileTap={disabled ? undefined : { scale: 0.95 }}
      transition={spring}
      className={cn(buttonBase, buttonSizes[size], buttonVariants[variant], full && 'w-full', className)}
      {...props}
    >
      {children}
    </motion.button>
  )
})

export function Spinner({ size = 16, className }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      style={{ width: size, height: size }}
      className={cn('inline-block animate-spin rounded-full border-2 border-white/25 border-t-white', className)}
    />
  )
}

/* ─────────────────────────── Chips & badges ─────────────────────────── */
const tones = {
  safe: 'text-emerald-300 light:text-emerald-700 bg-emerald-400/10 border-emerald-400/25',
  warning: 'text-amber-300 light:text-amber-700 bg-amber-400/10 border-amber-400/25',
  critical: 'text-rose-300 light:text-rose-700 bg-rose-400/10 border-rose-400/30',
  overdue: 'text-rose-300 light:text-rose-700 bg-rose-500/15 border-rose-400/35',
  info: 'text-sky-300 light:text-sky-700 bg-sky-400/10 border-sky-400/25',
  violet: 'text-violet-300 light:text-violet-700 bg-violet-400/10 border-violet-400/25',
  neutral: 'text-muted bg-glass border-line',
  unknown: 'text-muted bg-glass border-line',
}

export function Chip({ tone = 'neutral', children, className, dot }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-[3px] text-[0.7rem] font-medium leading-5 whitespace-nowrap',
        tones[tone] || tones.neutral,
        className
      )}
    >
      {dot && <span className="size-1.5 rounded-full bg-current shadow-[0_0_8px_currentColor]" />}
      {children}
    </span>
  )
}

export function ConfidenceBadge({ confidence }) {
  const labels = { high: 'High', medium: 'Moderate', low: 'Low' }
  const tone = { high: 'safe', medium: 'warning', low: 'critical' }[confidence] || 'neutral'
  return <Chip tone={tone}>{labels[confidence] || confidence}</Chip>
}

export function UrgencyChip({ days, label }) {
  if (days === null || days === undefined) return null
  const tone = days < 0 ? 'overdue' : days <= 7 ? 'critical' : days <= 30 ? 'warning' : 'safe'
  return <Chip tone={tone} dot>{label}</Chip>
}

export function StatusBadge({ status }) {
  if (status === 'checking')
    return (
      <Chip tone="neutral" className="gap-2">
        <Spinner size={10} className="border-muted/30 border-t-muted" /> <span className="hidden sm:inline">Connecting…</span>
      </Chip>
    )
  if (status === 'ok')
    return (
      <Chip tone="safe" className="gap-2">
        <span className="relative flex size-2">
          <span className="animate-ping-slow absolute inline-flex size-full rounded-full bg-emerald-400/70" />
          <span className="relative inline-flex size-2 rounded-full bg-emerald-400" />
        </span>
        <span className="hidden sm:inline">All Systems Operational</span>
        <span className="sm:hidden">Online</span>
      </Chip>
    )
  return (
    <Chip tone="critical" className="gap-2">
      <span className="size-2 rounded-full bg-rose-400" />
      <span className="hidden sm:inline">Service Unavailable</span>
      <span className="sm:hidden">Offline</span>
    </Chip>
  )
}

export function UserChip({ email }) {
  const initials = email ? email.slice(0, 2).toUpperCase() : '?'
  return (
    <span className="glass inline-flex max-w-full items-center gap-2.5 rounded-full py-1 pr-4 pl-1 text-sm text-muted">
      <span className="grid size-7 shrink-0 place-items-center rounded-full bg-linear-to-br from-violet-glow to-cyan-glow text-[0.65rem] font-bold text-white">
        {initials}
      </span>
      <span className="truncate">{email}</span>
    </span>
  )
}

/* ─────────────────────────── Form fields ─────────────────────────── */
export const fieldClass =
  'w-full rounded-xl border border-line bg-field px-3.5 py-2.5 text-sm text-fg placeholder:text-subtle outline-none backdrop-blur-md transition duration-200 hover:border-line-strong focus:border-violet-glow/70 focus:ring-4 focus:ring-violet-glow/15'

export const Input = forwardRef(function Input({ className, ...props }, ref) {
  return <input ref={ref} className={cn(fieldClass, className)} {...props} />
})

export const Textarea = forwardRef(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn(fieldClass, 'resize-y', className)} {...props} />
})

export function Select({ className, wrapClassName, children, ...props }) {
  return (
    <div className={cn('relative', wrapClassName)}>
      <select
        className={cn(fieldClass, 'cursor-pointer appearance-none pr-9 [&>option]:bg-[#0a0c1f] [&>option]:text-white light:[&>option]:bg-white light:[&>option]:text-[#12143a]', className)}
        {...props}
      >
        {children}
      </select>
      <Icon name="chevronDown" size={15} className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-subtle" />
    </div>
  )
}

export function Field({ label, value, onChange, type = 'text', id }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[0.7rem] font-semibold tracking-wider text-subtle uppercase">{label}</label>
      <Input id={id} type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={label} />
    </div>
  )
}

/* ─────────────────────────── Feedback ─────────────────────────── */
export function Notice({ tone = 'info', children, className }) {
  const t = {
    success: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200 light:text-emerald-800',
    error: 'border-rose-400/30 bg-rose-400/10 text-rose-200 light:text-rose-800',
    info: 'border-sky-400/30 bg-sky-400/10 text-sky-200 light:text-sky-800',
  }[tone]
  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      role={tone === 'error' ? 'alert' : 'status'}
      className={cn('flex items-start gap-2.5 rounded-xl border px-4 py-3 text-sm backdrop-blur-md', t, className)}
    >
      <Icon name={tone === 'success' ? 'check' : tone === 'error' ? 'alert' : 'info'} size={16} className="mt-0.5 shrink-0" />
      <div>{children}</div>
    </motion.div>
  )
}

export function Skeleton({ className }) {
  return <div className={cn('animate-skeleton rounded-lg bg-white/10 light:bg-indigo-900/10', className)} />
}

export function EmptyState({ icon = 'inbox', title, sub, action }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass flex flex-col items-center gap-3 rounded-2xl px-6 py-14 text-center"
    >
      <div className="animate-float grid size-16 place-items-center rounded-2xl bg-linear-to-br from-violet-glow/25 to-cyan-glow/20 text-violet-300 light:text-violet-700 ring-1 ring-line">
        <Icon name={icon} size={28} />
      </div>
      <h3 className="text-lg font-semibold">{title}</h3>
      {sub && <p className="max-w-sm text-sm text-muted">{sub}</p>}
      {action}
    </motion.div>
  )
}

export function ToastStack({ toasts, onRemove }) {
  const iconFor = { success: 'check', error: 'alert', info: 'info' }
  const ring = {
    success: 'border-emerald-400/40 text-emerald-300',
    error: 'border-rose-400/40 text-rose-300',
    info: 'border-sky-400/40 text-sky-300',
  }
  return (
    <div className="pointer-events-none fixed right-4 bottom-24 z-[100] flex w-[min(92vw,22rem)] flex-col gap-2 lg:bottom-6" aria-live="polite">
      <AnimatePresence initial={false}>
        {toasts.map(t => (
          <motion.div
            key={t.id}
            layout
            initial={{ opacity: 0, x: 60, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 60, scale: 0.9 }}
            transition={spring}
            className={cn('glass-strong pointer-events-auto flex items-start gap-3 rounded-xl px-4 py-3 text-sm', ring[t.type]?.split(' ')[0])}
            role={t.type === 'error' ? 'alert' : 'status'}
          >
            <Icon name={iconFor[t.type] || 'info'} size={17} className={cn('mt-0.5 shrink-0', ring[t.type]?.split(' ')[1])} />
            <span className="flex-1 text-fg">{t.message}</span>
            <button onClick={() => onRemove(t.id)} aria-label="Dismiss notification" className="text-subtle transition hover:text-fg">
              <Icon name="x" size={15} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

export function SectionTitle({ icon, title, sub, right, className }) {
  return (
    <div className={cn('mb-4 flex flex-wrap items-center justify-between gap-3', className)}>
      <div className="flex items-center gap-3">
        {icon && (
          <span className="grid size-9 place-items-center rounded-xl bg-linear-to-br from-violet-glow/25 to-cyan-glow/15 text-violet-300 light:text-violet-700 ring-1 ring-line">
            <Icon name={icon} size={17} />
          </span>
        )}
        <div>
          <h3 className="text-[1.02rem] leading-tight font-semibold">{title}</h3>
          {sub && <p className="mt-0.5 text-xs text-subtle">{sub}</p>}
        </div>
      </div>
      {right}
    </div>
  )
}

export function OnboardingSteps({ step }) {
  const steps = ['Connect Gmail', 'Scan Orders', 'Review Items']
  return (
    <ol className="mx-auto mb-6 flex w-full max-w-xl items-center" aria-label="Setup progress">
      {steps.map((label, i) => {
        const done = i < step
        const active = i === step
        return (
          <li key={label} className="flex flex-1 items-center last:flex-none" aria-current={active ? 'step' : undefined}>
            <div className="flex flex-col items-center gap-2">
              <motion.div
                animate={{ scale: active ? 1.12 : 1 }}
                transition={spring}
                className={cn(
                  'grid size-9 place-items-center rounded-full border text-sm font-semibold transition-colors',
                  done && 'border-transparent bg-linear-to-br from-emerald-400 to-cyan-400 text-slate-900',
                  active && 'border-violet-glow/70 bg-violet-glow/20 text-fg shadow-[0_0_24px_rgba(139,92,246,0.6)]',
                  !done && !active && 'border-line text-subtle'
                )}
              >
                {done ? <Icon name="check" size={16} strokeWidth={2.6} /> : i + 1}
              </motion.div>
              <span className={cn('text-[0.7rem] font-medium', active || done ? 'text-fg' : 'text-subtle')}>{label}</span>
            </div>
            {i < steps.length - 1 && (
              <div className="relative mx-2 mb-6 h-px flex-1 overflow-hidden bg-line">
                <motion.div
                  className="absolute inset-y-0 left-0 bg-linear-to-r from-violet-glow to-cyan-glow"
                  initial={false}
                  animate={{ width: done ? '100%' : '0%' }}
                  transition={{ duration: 0.6 }}
                />
              </div>
            )}
          </li>
        )
      })}
    </ol>
  )
}

