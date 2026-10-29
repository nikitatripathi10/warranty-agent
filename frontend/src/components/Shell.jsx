import { motion } from 'motion/react'
import Icon from './Icon'
import { StatusBadge, UserChip, spring } from './ui'
import PaletteSwitcher from './PaletteSwitcher'
import { cn } from '../lib/utils'

export function Logo({ compact = false, onClick }) {
  return (
    <div
      onClick={onClick}
      className={cn('flex items-center gap-3', onClick && 'cursor-pointer hover:opacity-90 transition')}
    >
      <div className="relative grid size-10 place-items-center overflow-hidden rounded-xl bg-linear-to-br from-violet-glow via-electric to-cyan-glow text-white shadow-[0_0_28px_rgba(99,102,241,0.7)]">
        <span className="animate-radar absolute inset-0 bg-[conic-gradient(from_0deg,transparent_0deg,rgba(255,255,255,0.55)_40deg,transparent_70deg)]" />
        <Icon name="shieldCheck" size={20} className="relative" strokeWidth={2} />
      </div>
      {!compact && (
        <div className="leading-tight">
          <div className="font-display text-[1.05rem] font-bold tracking-tight">Warranty Radar</div>
          <div className="text-[0.62rem] font-medium tracking-[0.18em] text-subtle uppercase">Nikita Tripathi · MITS-DU</div>
        </div>
      )}
    </div>
  )
}

export function ThemeToggle({ theme, onToggle, className }) {
  const next = theme === 'dark' ? 'light' : 'dark'
  return (
    <motion.button
      id="btn-theme-toggle"
      type="button"
      onClick={onToggle}
      whileHover={{ scale: 1.08, rotate: 12 }}
      whileTap={{ scale: 0.88 }}
      transition={spring}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
      className={cn('glass grid size-10 place-items-center rounded-xl text-muted transition-colors hover:text-fg', className)}
    >
      <motion.span key={theme} initial={{ rotate: -90, opacity: 0, scale: 0.5 }} animate={{ rotate: 0, opacity: 1, scale: 1 }} transition={{ duration: 0.35 }}>
        <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={18} />
      </motion.span>
    </motion.button>
  )
}

/* ── Top navbar ───────────────────────────────────────────────────────────── */
export function TopNav({
  healthStatus,
  theme,
  onToggleTheme,
  activePalette,
  onSelectPalette,
  onOpenDashboard,
  onNavigate,
  currentScreen = 'landing',
}) {
  const navItems = [
    { id: 'landing', label: 'Overview', icon: 'sparkles' },
    { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
    { id: 'alerts', label: 'Alerts', icon: 'bell', badge: '2' },
    { id: 'upload', label: 'OCR Ingest', icon: 'upload' },
    { id: 'lookup', label: 'AI Copilot', icon: 'bot' },
    { id: 'validation', label: 'Validation', icon: 'check', badge: '94.6%' },
    { id: 'dossier', label: 'MITS Dossier', icon: 'file' },
  ]

  return (
    <motion.header
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 160, damping: 20 }}
      className="sticky top-3 z-40 mx-auto mt-3 flex w-[min(96%,76rem)] items-center justify-between rounded-2xl glass-strong px-4 py-2.5 sm:px-5"
    >
      <Logo onClick={onOpenDashboard} />

      {/* Segregated Quick-Jump Navigation Links */}
      {onNavigate && (
        <nav className="hidden xl:flex items-center gap-1" aria-label="Quick jump">
          {navItems.map(item => {
            const active = currentScreen === item.id
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onNavigate(item.id)}
                className={cn(
                  'relative flex items-center gap-1.5 rounded-xl px-2.5 py-1.5 text-xs font-semibold transition-all',
                  active ? 'text-fg bg-white/10 shadow-sm' : 'text-subtle hover:text-fg hover:bg-white/5'
                )}
              >
                <Icon name={item.icon} size={13} />
                <span>{item.label}</span>
                {item.badge && (
                  <span className="rounded-full bg-violet-500/20 px-1.5 py-0.2 text-[0.6rem] font-bold text-violet-300">
                    {item.badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>
      )}

      <div className="flex items-center gap-2.5">
        {onOpenDashboard && (
          <button
            type="button"
            onClick={onOpenDashboard}
            className="flex items-center gap-2 rounded-xl bg-linear-to-r from-violet-600 to-cyan-500 px-3.5 py-1.5 text-xs font-semibold text-white shadow-md hover:opacity-95 transition"
          >
            <Icon name="dashboard" size={14} />
            <span className="hidden sm:inline">Launch Pilot Workspace</span>
          </button>
        )}
        <StatusBadge status={healthStatus} />
        {activePalette && onSelectPalette && (
          <PaletteSwitcher activePalette={activePalette} onSelectPalette={onSelectPalette} />
        )}
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
    </motion.header>
  )
}

export const NAV = [
  { id: 'dashboard', label: 'Executive Dashboard', icon: 'dashboard', badge: null },
  { id: 'alerts', label: 'Alerts & Recalls', icon: 'bell', badge: '2', badgeClass: 'bg-rose-500 text-white' },
  { id: 'upload', label: 'Document Ingestion (OCR)', icon: 'upload', badge: 'OCR', badgeClass: 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' },
  { id: 'lookup', label: 'AI Policy Extractor', icon: 'search', badge: 'NLP', badgeClass: 'bg-violet-500/20 text-violet-300 border border-violet-500/30' },
  { id: 'validation', label: 'Milestone 4 Benchmarks', icon: 'check', badge: '94.6%', badgeClass: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' },
  { id: 'dossier', label: 'MITS Project Dossier', icon: 'file', badge: 'M2–M5', badgeClass: 'bg-amber-500/20 text-amber-300 border border-amber-500/30' },
]

const isActive = (screen, id) => screen === id || (screen === 'detail' && id === 'dashboard')

/* ── Desktop sidebar ─────────────────────────────────────────────────────── */
export function Sidebar({
  screen,
  onNavigate,
  alertCount,
  healthStatus,
  theme,
  onToggleTheme,
  userEmail,
  onSignOut,
  activePalette,
  onSelectPalette,
}) {
  return (
    <motion.aside
      initial={{ x: -40, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 150, damping: 22 }}
      className="glass-strong fixed top-3 bottom-3 left-3 z-40 hidden w-[17.5rem] flex-col rounded-3xl p-4 lg:flex overflow-y-auto"
      aria-label="Primary"
    >
      <div className="px-2 pt-1 pb-4">
        <Logo onClick={() => onNavigate('dashboard')} />
      </div>

      <nav className="flex flex-1 flex-col gap-1" aria-label="Main navigation">
        <div className="px-3 pb-2 text-[0.65rem] font-semibold tracking-[0.18em] text-subtle uppercase">System Navigation</div>
        {NAV.map(item => {
          const active = isActive(screen, item.id)
          return (
            <motion.button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              whileHover={{ x: 3 }}
              whileTap={{ scale: 0.97 }}
              transition={spring}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'group relative flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-left text-xs font-semibold transition-colors',
                active ? 'text-fg' : 'text-muted hover:text-fg'
              )}
            >
              {active && (
                <motion.span
                  layoutId="nav-active"
                  transition={spring}
                  className="absolute inset-0 rounded-xl border border-violet-glow/35 bg-linear-to-r from-violet-glow/25 via-electric/10 to-transparent shadow-[0_0_30px_-8px_rgba(139,92,246,0.7)]"
                />
              )}
              <Icon name={item.icon} size={17} className={cn('relative transition-colors', active && 'text-violet-300 light:text-violet-700')} />
              <span className="relative flex-1 truncate">{item.label}</span>
              {item.id === 'alerts' && alertCount > 0 ? (
                <span className="relative grid min-w-5 place-items-center rounded-full bg-rose-500 px-1.5 text-[0.65rem] font-bold text-white shadow-[0_0_12px_rgba(244,63,94,0.7)]">
                  {alertCount}
                </span>
              ) : item.badge ? (
                <span className={cn('relative grid place-items-center rounded-full px-1.5 py-0.5 text-[0.62rem] font-bold shadow-sm', item.badgeClass)}>
                  {item.badge}
                </span>
              ) : null}
            </motion.button>
          )
        })}

        {/* Link back to Onboarding & Tour */}
        <div className="pt-2 mt-2 border-t border-line/40">
          <button
            type="button"
            onClick={() => onNavigate('landing')}
            className={cn(
              'flex items-center gap-2.5 rounded-xl px-3.5 py-2 text-left text-xs font-medium text-subtle hover:text-fg transition-colors w-full',
              screen === 'landing' && 'text-fg font-semibold bg-white/5'
            )}
          >
            <Icon name="sparkles" size={15} className="text-cyan-glow" />
            <span>Onboarding Tour &amp; Specs</span>
          </button>
        </div>
      </nav>

      <div className="mt-3 flex flex-col gap-2.5 border-t border-line pt-3">
        {activePalette && onSelectPalette && (
          <div className="flex items-center justify-between">
            <span className="text-[0.65rem] font-semibold tracking-[0.16em] text-subtle uppercase">FX Theme</span>
            <PaletteSwitcher activePalette={activePalette} onSelectPalette={onSelectPalette} />
          </div>
        )}
        <div className="flex items-center justify-between gap-2">
          <StatusBadge status={healthStatus} />
          <ThemeToggle theme={theme} onToggle={onToggleTheme} className="size-8" />
        </div>
        <UserChip email={userEmail} />
        <motion.button
          type="button"
          onClick={onSignOut}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.96 }}
          transition={spring}
          className="flex items-center justify-center gap-2 rounded-xl border border-line px-3 py-1.5 text-xs text-muted transition-colors hover:border-rose-400/40 hover:bg-rose-500/10 hover:text-rose-300"
        >
          <Icon name="logout" size={14} /> Switch Account / Logout
        </motion.button>
      </div>
    </motion.aside>
  )
}

/* ── Mobile / tablet top bar + bottom tab bar ────────────────────────────── */
export function MobileTopBar({
  healthStatus,
  theme,
  onToggleTheme,
  onSignOut,
  activePalette,
  onSelectPalette,
  onNavigate,
}) {
  return (
    <header className="glass-strong sticky top-2 z-40 mx-2 mt-2 flex items-center justify-between rounded-2xl px-3.5 py-2 lg:hidden">
      <Logo compact onClick={() => onNavigate && onNavigate('dashboard')} />
      <div className="flex items-center gap-2">
        {activePalette && onSelectPalette && (
          <PaletteSwitcher activePalette={activePalette} onSelectPalette={onSelectPalette} />
        )}
        <StatusBadge status={healthStatus} />
        <ThemeToggle theme={theme} onToggle={onToggleTheme} className="size-8" />
        <button type="button" onClick={onSignOut} aria-label="Sign out"
          className="glass grid size-8 place-items-center rounded-xl text-muted transition hover:text-rose-300">
          <Icon name="logout" size={15} />
        </button>
      </div>
    </header>
  )
}

export function MobileTabBar({ screen, onNavigate, alertCount }) {
  const mobileNav = [
    { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
    { id: 'alerts', label: 'Alerts', icon: 'bell' },
    { id: 'upload', label: 'Ingest', icon: 'upload' },
    { id: 'validation', label: 'Metrics', icon: 'check' },
    { id: 'dossier', label: 'MITS', icon: 'file' },
  ]

  return (
    <nav
      aria-label="Main navigation"
      className="glass-strong fixed inset-x-3 bottom-3 z-40 grid grid-cols-5 rounded-2xl p-1.5 pb-[max(0.375rem,env(safe-area-inset-bottom))] lg:hidden"
    >
      {mobileNav.map(item => {
        const active = isActive(screen, item.id)
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            aria-current={active ? 'page' : undefined}
            className={cn('relative flex flex-col items-center gap-1 rounded-xl py-2 text-[0.62rem] font-medium transition-colors', active ? 'text-fg' : 'text-subtle')}
          >
            {active && (
              <motion.span layoutId="tab-active" transition={spring}
                className="absolute inset-0 rounded-xl border border-violet-glow/35 bg-violet-glow/20 shadow-[0_0_24px_-6px_rgba(139,92,246,0.8)]" />
            )}
            <span className="relative">
              <Icon name={item.icon} size={18} />
              {item.id === 'alerts' && alertCount > 0 && (
                <span className="absolute -top-1.5 -right-2.5 grid min-w-4 place-items-center rounded-full bg-rose-500 px-1 text-[0.58rem] font-bold text-white">{alertCount}</span>
              )}
            </span>
            <span className="relative truncate max-w-[4rem]">
              {item.label}
            </span>
          </button>
        )
      })}
    </nav>
  )
}

export function Footer({ className }) {
  return (
    <footer className={cn('mt-16 border-t border-line py-6 text-xs text-subtle', className)}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-medium text-muted">
          <Icon name="shieldCheck" size={15} className="text-violet-300 light:text-violet-700" />
          <span>Warranty Radar · Submitted by Nikita Tripathi</span>
        </div>
        <div>Macro Project | Skills Development Monitoring System, MITS-DU Gwalior</div>
        <div>Milestones 2, 3, 4 &amp; 5 · Deadline: 30 October 2026</div>
      </div>
    </footer>
  )
}
