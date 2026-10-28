import { motion } from 'motion/react'
import Icon from './Icon'
import { StatusBadge, UserChip, spring } from './ui'
import { cn } from '../lib/utils'

export function Logo({ compact = false }) {
  return (
    <div className="flex items-center gap-3">
      <div className="relative grid size-10 place-items-center overflow-hidden rounded-xl bg-linear-to-br from-violet-glow via-electric to-cyan-glow text-white shadow-[0_0_28px_rgba(99,102,241,0.7)]">
        <span className="animate-radar absolute inset-0 bg-[conic-gradient(from_0deg,transparent_0deg,rgba(255,255,255,0.55)_40deg,transparent_70deg)]" />
        <Icon name="shieldCheck" size={20} className="relative" strokeWidth={2} />
      </div>
      {!compact && (
        <div className="leading-tight">
          <div className="font-display text-[1.05rem] font-bold tracking-tight">Warranty Radar</div>
          <div className="text-[0.62rem] font-medium tracking-[0.18em] text-subtle uppercase">v0.4 · Purchase guardian</div>
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

/* ── Landing navbar (signed-out) ─────────────────────────────────────────── */
export function TopNav({ healthStatus, theme, onToggleTheme }) {
  return (
    <motion.header
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 160, damping: 20 }}
      className="sticky top-3 z-40 mx-auto mt-3 flex w-[min(96%,72rem)] items-center justify-between rounded-2xl glass-strong px-4 py-2.5 sm:px-5"
    >
      <Logo />
      <div className="flex items-center gap-2.5">
        <StatusBadge status={healthStatus} />
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
    </motion.header>
  )
}

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
  { id: 'alerts', label: 'Alerts', icon: 'bell' },
  { id: 'upload', label: 'Upload', icon: 'upload' },
  { id: 'lookup', label: 'Quick Lookup', icon: 'search' },
]

const isActive = (screen, id) => screen === id || (screen === 'detail' && id === 'dashboard')

/* ── Desktop sidebar ─────────────────────────────────────────────────────── */
export function Sidebar({ screen, onNavigate, alertCount, healthStatus, theme, onToggleTheme, userEmail, onSignOut }) {
  return (
    <motion.aside
      initial={{ x: -40, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 150, damping: 22 }}
      className="glass-strong fixed top-3 bottom-3 left-3 z-40 hidden w-[17rem] flex-col rounded-3xl p-4 lg:flex"
      aria-label="Primary"
    >
      <div className="px-2 pt-1 pb-5"><Logo /></div>

      <nav className="flex flex-1 flex-col gap-1" aria-label="Main navigation">
        <div className="px-3 pb-2 text-[0.65rem] font-semibold tracking-[0.18em] text-subtle uppercase">Menu</div>
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
                'group relative flex items-center gap-3 rounded-xl px-3.5 py-3 text-left text-sm font-medium transition-colors',
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
              <Icon name={item.icon} size={18} className={cn('relative transition-colors', active && 'text-violet-300 light:text-violet-700')} />
              <span className="relative flex-1">{item.label}</span>
              {item.id === 'alerts' && alertCount > 0 && (
                <span className="relative grid min-w-5 place-items-center rounded-full bg-rose-500 px-1.5 text-[0.65rem] font-bold text-white shadow-[0_0_12px_rgba(244,63,94,0.7)]">
                  {alertCount}
                </span>
              )}
            </motion.button>
          )
        })}
      </nav>

      <div className="mt-4 flex flex-col gap-3 border-t border-line pt-4">
        <div className="flex items-center justify-between gap-2">
          <StatusBadge status={healthStatus} />
          <ThemeToggle theme={theme} onToggle={onToggleTheme} className="size-9" />
        </div>
        <UserChip email={userEmail} />
        <motion.button
          type="button"
          onClick={onSignOut}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.96 }}
          transition={spring}
          className="flex items-center justify-center gap-2 rounded-xl border border-line px-3 py-2.5 text-sm text-muted transition-colors hover:border-rose-400/40 hover:bg-rose-500/10 hover:text-rose-300"
        >
          <Icon name="logout" size={16} /> Sign out
        </motion.button>
      </div>
    </motion.aside>
  )
}

/* ── Mobile / tablet top bar + bottom tab bar ────────────────────────────── */
export function MobileTopBar({ healthStatus, theme, onToggleTheme, onSignOut }) {
  return (
    <header className="glass-strong sticky top-2 z-40 mx-2 mt-2 flex items-center justify-between rounded-2xl px-3.5 py-2 lg:hidden">
      <Logo compact />
      <div className="flex items-center gap-2">
        <StatusBadge status={healthStatus} />
        <ThemeToggle theme={theme} onToggle={onToggleTheme} className="size-9" />
        <button type="button" onClick={onSignOut} aria-label="Sign out"
          className="glass grid size-9 place-items-center rounded-xl text-muted transition hover:text-rose-300">
          <Icon name="logout" size={16} />
        </button>
      </div>
    </header>
  )
}

export function MobileTabBar({ screen, onNavigate, alertCount }) {
  return (
    <nav
      aria-label="Main navigation"
      className="glass-strong fixed inset-x-3 bottom-3 z-40 grid grid-cols-4 rounded-2xl p-1.5 pb-[max(0.375rem,env(safe-area-inset-bottom))] lg:hidden"
    >
      {NAV.map(item => {
        const active = isActive(screen, item.id)
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            aria-current={active ? 'page' : undefined}
            className={cn('relative flex flex-col items-center gap-1 rounded-xl py-2 text-[0.66rem] font-medium transition-colors', active ? 'text-fg' : 'text-subtle')}
          >
            {active && (
              <motion.span layoutId="tab-active" transition={spring}
                className="absolute inset-0 rounded-xl border border-violet-glow/35 bg-violet-glow/20 shadow-[0_0_24px_-6px_rgba(139,92,246,0.8)]" />
            )}
            <span className="relative">
              <Icon name={item.icon} size={20} />
              {item.id === 'alerts' && alertCount > 0 && (
                <span className="absolute -top-1.5 -right-2.5 grid min-w-4 place-items-center rounded-full bg-rose-500 px-1 text-[0.58rem] font-bold text-white">{alertCount}</span>
              )}
            </span>
            <span className="relative">{item.id === 'lookup' ? 'Lookup' : item.label}</span>
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
          <Icon name="shieldCheck" size={15} className="text-violet-300 light:text-violet-700" /> Warranty Radar
        </div>
        <div>Protecting purchases across 10+ Indian retailers</div>
        <div>© {new Date().getFullYear()} Warranty Radar · v0.4.0</div>
      </div>
    </footer>
  )
}

