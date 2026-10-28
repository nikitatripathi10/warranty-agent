import { motion } from 'motion/react'
import { useId, useState } from 'react'
import { cn } from '../lib/utils'

/* ── Donut chart ─────────────────────────────────────────────────────────── */
export function Donut({ segments, size = 168, thickness = 16, children }) {
  const total = segments.reduce((a, s) => a + s.value, 0)
  const r = (size - thickness) / 2
  const C = 2 * Math.PI * r
  let acc = 0
  const gap = total > 0 && segments.filter(s => s.value > 0).length > 1 ? 3 : 0

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" role="img"
        aria-label={`Warranty status: ${segments.map(s => `${s.value} ${s.label}`).join(', ')}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="currentColor" strokeWidth={thickness} className="text-line" />
        {total > 0 && segments.map((s, i) => {
          if (!s.value) return null
          const len = Math.max(0, (s.value / total) * C - gap)
          const offset = acc
          acc += (s.value / total) * C
          return (
            <motion.circle
              key={s.label}
              cx={size / 2}
              cy={size / 2}
              r={r}
              fill="none"
              stroke={s.color}
              strokeWidth={thickness}
              strokeLinecap="round"
              strokeDashoffset={-offset}
              initial={{ strokeDasharray: `0 ${C}` }}
              animate={{ strokeDasharray: `${len} ${C - len}` }}
              transition={{ duration: 1.1, delay: 0.15 + i * 0.12, ease: [0.22, 1, 0.36, 1] }}
              style={{ filter: `drop-shadow(0 0 6px ${s.color}88)` }}
            />
          )
        })}
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">{children}</div>
    </div>
  )
}

/* ── Vertical bar chart (e.g. spend per month) ───────────────────────────── */
export function BarChart({ data, height = 150, format = v => v }) {
  const max = Math.max(1, ...data.map(d => d.value))
  const [hover, setHover] = useState(null)
  const gid = useId().replace(/:/g, '')
  return (
    <div className="flex w-full items-end gap-2 sm:gap-3" style={{ height }} role="img"
      aria-label={`Bar chart: ${data.map(d => `${d.label} ${format(d.value)}`).join(', ')}`}>
      <svg width="0" height="0" aria-hidden="true">
        <defs>
          <linearGradient id={`bar-${gid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#22d3ee" />
            <stop offset="100%" stopColor="#8b5cf6" />
          </linearGradient>
        </defs>
      </svg>
      {data.map((d, i) => {
        const h = Math.max(d.value ? 6 : 3, (d.value / max) * (height - 38))
        const active = hover === i
        return (
          <div
            key={d.label}
            className="group relative flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-2"
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          >
            <div
              className={cn(
                'pointer-events-none absolute -top-1 z-10 rounded-md border border-line bg-glass-strong px-2 py-1 text-[0.68rem] font-medium whitespace-nowrap text-fg opacity-0 shadow-lg backdrop-blur-md transition-opacity',
                active && 'opacity-100'
              )}
              style={{ bottom: h + 30, top: 'auto' }}
            >
              {format(d.value)}
            </div>
            <motion.div
              className={cn('w-full max-w-10 rounded-t-lg rounded-b-sm', d.value ? 'bg-linear-to-t from-violet-glow to-cyan-glow' : 'bg-line')}
              initial={{ height: 0 }}
              whileInView={{ height: h }}
              viewport={{ once: true }}
              transition={{ type: 'spring', stiffness: 90, damping: 16, delay: i * 0.07 }}
              style={{ boxShadow: active && d.value ? '0 0 22px rgba(34,211,238,0.55)' : d.value ? '0 0 14px rgba(139,92,246,0.35)' : 'none', opacity: active || hover === null ? 1 : 0.55 }}
            />
            <span className="text-[0.68rem] text-subtle">{d.label}</span>
          </div>
        )
      })}
    </div>
  )
}

/* ── Horizontal ranked bars (top retailers) ──────────────────────────────── */
export function HBars({ data, format = v => v }) {
  const max = Math.max(1, ...data.map(d => d.value))
  return (
    <ul className="flex flex-col gap-3.5">
      {data.map((d, i) => (
        <li key={d.label}>
          <div className="mb-1.5 flex items-center justify-between gap-3 text-[0.8rem]">
            <span className="truncate font-medium">{d.label}</span>
            <span className="shrink-0 text-muted tabular-nums">{format(d.value)} <span className="text-subtle">· {d.count}</span></span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-line">
            <motion.div
              className="h-full rounded-full bg-linear-to-r from-violet-glow via-electric to-cyan-glow"
              initial={{ width: 0 }}
              whileInView={{ width: `${Math.max(4, (d.value / max) * 100)}%` }}
              viewport={{ once: true }}
              transition={{ duration: 0.9, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] }}
              style={{ boxShadow: '0 0 12px rgba(99,102,241,0.55)' }}
            />
          </div>
        </li>
      ))}
    </ul>
  )
}

/* ── Decorative sparkline ────────────────────────────────────────────────── */
export function Sparkline({ values, color = '#8b5cf6', className }) {
  const gid = useId().replace(/:/g, '')
  const w = 120
  const h = 36
  const pts = values.length > 1 ? values : [0, 0]
  const max = Math.max(...pts)
  const min = Math.min(...pts)
  const span = max - min || 1
  const coords = pts.map((v, i) => [(i / (pts.length - 1)) * w, h - 4 - ((v - min) / span) * (h - 10)])
  const d = coords.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={cn('h-9 w-full', className)} preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id={`sp-${gid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${d} L${w} ${h} L0 ${h} Z`} fill={`url(#sp-${gid})`} />
      <motion.path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.4, ease: 'easeOut' }}
        style={{ filter: `drop-shadow(0 0 4px ${color})` }}
      />
    </svg>
  )
}

