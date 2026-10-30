import { useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { NumberTicker } from '../components/magicui/number-ticker'
import { GlassCard, Button, Spinner, Select, Skeleton, EmptyState, containerStagger, itemRise } from '../components/ui'
import TiltCard from '../components/reactbits/TiltCard'
import { ANIMATION_PALETTES } from '../lib/animation-theme'
import WarrantyTimeline from '../components/WarrantyTimeline'
import PurchaseCard from '../components/PurchaseCard'
import PurchaseListItem from '../components/PurchaseListItem'
import { Donut, BarChart, HBars, Sparkline } from '../components/charts'
import { daysUntil, fmtCompactINR, greeting } from '../lib/format'
import Icon from '../components/Icon'

export default function DashboardView({
  userEmail,
  activePalette = 'cyberpunk',
  purchases,
  purchasesLoading,
  purchasesError,
  alerts,
  onAlertsClick,
  onScanInbox,
  fetchLoading,
  fetchResult,
  fetchError,
  hasOnboarded,
  onboardStep,
  onFinishOnboarding,
  onOpenDetail,
  onNavigate,
  searchQ,
  setSearchQ,
  filterBrand,
  setFilterBrand,
  filterStatus,
  setFilterStatus,
  filterConf,
  setFilterConf,
  sortBy,
  setSortBy,
  viewMode,
  setViewMode,
  clearFilters,
  hasActiveFilters,
}) {
  const [showAnalytics, setShowAnalytics] = useState(true)
  const palette = ANIMATION_PALETTES[activePalette] || ANIMATION_PALETTES.cyberpunk

  // ── Metrics Calculation ──────────────────────────────────────────────────────
  const totalValue = useMemo(() => {
    return purchases.reduce((acc, p) => acc + (Number(p.price) || 0), 0)
  }, [purchases])

  const expiringSoonCount = useMemo(() => {
    return purchases.filter(p => {
      const d = p.warranty_period?.warranty_end_date
      if (!d) return false
      const days = daysUntil(d)
      return days !== null && days >= 0 && days <= 30
    }).length
  }, [purchases])

  const overdueCount = useMemo(() => {
    return purchases.filter(p => {
      const d = p.warranty_period?.warranty_end_date
      if (!d) return false
      const days = daysUntil(d)
      return days !== null && days < 0
    }).length
  }, [purchases])

  const safeCount = Math.max(0, purchases.length - expiringSoonCount - overdueCount)

  // ── Retailer / Brand Breakdown ────────────────────────────────────────────────
  const topRetailers = useMemo(() => {
    const map = new Map()
    purchases.forEach(p => {
      const name = p.retailer || p.brand || 'Other'
      const existing = map.get(name) || { value: 0, count: 0 }
      map.set(name, {
        value: existing.value + (Number(p.price) || 0),
        count: existing.count + 1,
      })
    })
    return [...map.entries()]
      .map(([label, stats]) => ({ label, value: stats.value, count: stats.count }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 5)
  }, [purchases])

  // ── Monthly Distribution ─────────────────────────────────────────────────────
  const monthlyData = useMemo(() => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    const bucket = {}
    const now = new Date()
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
      const key = `${months[d.getMonth()]}`
      bucket[key] = 0
    }
    purchases.forEach(p => {
      if (!p.purchase_date) return
      const d = new Date(p.purchase_date + 'T00:00:00')
      const key = months[d.getMonth()]
      if (bucket[key] !== undefined) {
        bucket[key] += Number(p.price) || 0
      }
    })
    return Object.entries(bucket).map(([label, value]) => ({ label, value }))
  }, [purchases])

  const uniqueBrands = useMemo(() => {
    const s = new Set(purchases.map(p => p.retailer || p.brand).filter(Boolean))
    return [...s].sort()
  }, [purchases])

  // ── Filtered & Sorted Purchases ──────────────────────────────────────────────
  const filteredPurchases = useMemo(() => {
    let list = [...purchases]

    if (searchQ) {
      const q = searchQ.toLowerCase()
      list = list.filter(p =>
        (p.product_name || '').toLowerCase().includes(q) ||
        (p.retailer || '').toLowerCase().includes(q) ||
        (p.brand || '').toLowerCase().includes(q)
      )
    }

    if (filterBrand) {
      list = list.filter(p => (p.retailer || p.brand || '') === filterBrand)
    }

    if (filterConf) {
      list = list.filter(p => (p.warranty_period?.confidence_score || 'low') === filterConf)
    }

    if (filterStatus === 'expiring') {
      list = list.filter(p => {
        const d = p.warranty_period?.warranty_end_date
        if (!d) return false
        const days = daysUntil(d)
        return days !== null && days >= 0 && days <= 30
      })
    } else if (filterStatus === 'overdue') {
      list = list.filter(p => {
        const d = p.warranty_period?.warranty_end_date
        if (!d) return false
        return daysUntil(d) < 0
      })
    } else if (filterStatus === 'safe') {
      list = list.filter(p => {
        const d = p.warranty_period?.warranty_end_date
        if (!d) return true
        const days = daysUntil(d)
        return days !== null && days > 30
      })
    }

    if (sortBy === 'date_asc') {
      list.sort((a, b) => (a.purchase_date || '').localeCompare(b.purchase_date || ''))
    } else if (sortBy === 'date_desc') {
      list.sort((a, b) => (b.purchase_date || '').localeCompare(a.purchase_date || ''))
    } else if (sortBy === 'warranty_asc') {
      list.sort((a, b) => {
        const da = a.warranty_period?.warranty_end_date || '9999-12-31'
        const db = b.warranty_period?.warranty_end_date || '9999-12-31'
        return da.localeCompare(db)
      })
    } else if (sortBy === 'price_desc') {
      list.sort((a, b) => (Number(b.price) || 0) - (Number(a.price) || 0))
    } else if (sortBy === 'name_asc') {
      list.sort((a, b) => (a.product_name || '').localeCompare(b.product_name || ''))
    }

    return list
  }, [purchases, searchQ, filterBrand, filterConf, filterStatus, sortBy])

  const lowConfPurchases = purchases.filter(p => (p.warranty_period?.confidence_score || 'low') === 'low')

  return (
    <div className="space-y-6">
      {/* ── Top greeting banner ───────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-display text-2xl font-bold tracking-tight text-fg sm:text-3xl">
            {greeting()}, <span className="text-aurora">{userEmail.split('@')[0]}</span>
          </h2>
          <p className="mt-1 text-xs text-muted">
            Warranty Radar is actively monitoring your connected accounts &amp; invoices.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="secondary"
            size="md"
            onClick={() => onNavigate('connect')}
          >
            <Icon name="sparkles" size={16} />
            <span>Workspace</span>
          </Button>

          <Button
            variant="secondary"
            size="md"
            onClick={() => onNavigate('upload')}
          >
            <Icon name="upload" size={16} />
            <span>Upload Receipt</span>
          </Button>

          <Button
            id="btn-fetch-emails"
            variant="primary"
            size="md"
            onClick={onScanInbox}
            disabled={fetchLoading}
          >
            {fetchLoading ? (
              <>
                <Spinner size={15} />
                <span>Scanning Gmail…</span>
              </>
            ) : (
              <>
                <Icon name="search" size={16} />
                <span>Scan Inbox</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* ── Scan Notification ─────────────────────────────────────────────── */}
      <AnimatePresence>
        {fetchResult && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="glass-strong flex items-center justify-between rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200"
          >
            <div className="flex items-center gap-2.5">
              <Icon name="check" size={17} className="text-emerald-400" />
              <span>
                Scanned {fetchResult.emails_scanned} emails · Saved {fetchResult.purchases_created} new purchase records
                {fetchResult.purchases_failed > 0 && ` · ${fetchResult.purchases_failed} skipped`}
              </span>
            </div>
          </motion.div>
        )}
        {fetchError && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="glass-strong flex items-center gap-2.5 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200"
          >
            <Icon name="alert" size={17} className="text-rose-400" />
            <span>Scan failed: {fetchError}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Onboarding Banner (if setup not finalized) ─────────────────────── */}
      {!hasOnboarded && onboardStep < 3 && (
        <GlassCard beam beamColors={['#8b5cf6', '#22d3ee']} className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-violet-glow/20 text-cyan-glow ring-1 ring-line">
                <Icon name="sparkles" size={20} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-fg">
                  {onboardStep === 1 ? 'Step 2: Scan your Gmail for purchases' : 'Step 3: Review your imported records'}
                </h3>
                <p className="mt-1 text-xs text-muted">
                  {onboardStep === 1
                    ? 'Run a fast scan of your inbox to automatically index orders from Amazon, Flipkart, Blinkit, and more.'
                    : `We extracted ${purchases.length} items. Review ${lowConfPurchases.length} low-confidence items or finish setup.`}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              {onboardStep === 1 ? (
                <Button variant="primary" size="sm" onClick={onScanInbox} disabled={fetchLoading}>
                  {fetchLoading ? <Spinner size={14} /> : 'Scan Inbox Now'}
                </Button>
              ) : (
                <>
                  {lowConfPurchases.length > 0 && (
                    <Button variant="secondary" size="sm" onClick={() => setFilterConf('low')}>
                      Review Low-Confidence ({lowConfPurchases.length})
                    </Button>
                  )}
                  <Button variant="primary" size="sm" onClick={onFinishOnboarding}>
                    Finish Setup ✓
                  </Button>
                </>
              )}
            </div>
          </div>
        </GlassCard>
      )}

      {/* ── Key Metrics Summary Cards ─────────────────────────────────────── */}
      {purchasesLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <GlassCard key={i} className="p-5">
              <Skeleton className="mb-2 h-4 w-24" />
              <Skeleton className="mb-1 h-8 w-16" />
              <Skeleton className="h-3 w-32" />
            </GlassCard>
          ))}
        </div>
      ) : (
        <motion.div
          variants={containerStagger}
          initial="hidden"
          animate="show"
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          {/* Total Tracked */}
          <motion.div variants={itemRise}>
            <TiltCard maxTilt={8} className="h-full">
              <GlassCard className="p-5 h-full" intensity={0.1}>
                <div className="flex items-center justify-between text-xs text-subtle">
                  <span className="font-semibold uppercase tracking-wider">Total Tracked</span>
                  <span className="grid size-8 place-items-center rounded-lg bg-glass text-violet-300">
                    <Icon name="package" size={17} />
                  </span>
                </div>
                <div className="my-2 font-display text-3xl font-bold tracking-tight text-fg">
                  <NumberTicker value={purchases.length} />
                </div>
                <div className="flex items-center justify-between text-xs text-muted">
                  <span>Active purchase items</span>
                  <Sparkline values={[4, 7, 10, 8, 14, 18, purchases.length]} color={palette.primary} className="w-16" />
                </div>
              </GlassCard>
            </TiltCard>
          </motion.div>

          {/* Expiring Soon */}
          <motion.div variants={itemRise}>
            <TiltCard maxTilt={8} className="h-full">
              <GlassCard
                interactive
                onClick={onAlertsClick}
                className="p-5 h-full cursor-pointer hover:border-amber-400/50"
                intensity={0.1}
              >
                <div className="flex items-center justify-between text-xs text-subtle">
                  <span className="font-semibold uppercase tracking-wider">Expiring Soon</span>
                  <span className="grid size-8 place-items-center rounded-lg bg-amber-400/10 text-amber-300">
                    <Icon name="clock" size={17} />
                  </span>
                </div>
                <div className="my-2 font-display text-3xl font-bold tracking-tight text-amber-300">
                  <NumberTicker value={expiringSoonCount} />
                </div>
                <div className="text-xs text-muted">Next 30 days window</div>
              </GlassCard>
            </TiltCard>
          </motion.div>

          {/* Active Alerts */}
          <motion.div variants={itemRise}>
            <TiltCard maxTilt={8} className="h-full">
              <GlassCard
                interactive
                onClick={onAlertsClick}
                className="p-5 h-full cursor-pointer hover:border-rose-400/50"
                intensity={0.1}
              >
                <div className="flex items-center justify-between text-xs text-subtle">
                  <span className="font-semibold uppercase tracking-wider">Active Alerts</span>
                  <span className="grid size-8 place-items-center rounded-lg bg-rose-400/10 text-rose-300">
                    <Icon name="bell" size={17} />
                  </span>
                </div>
                <div className="my-2 font-display text-3xl font-bold tracking-tight text-rose-300">
                  <NumberTicker value={alerts.length} />
                </div>
                <div className="text-xs text-muted">Return &amp; warranty reminders</div>
              </GlassCard>
            </TiltCard>
          </motion.div>

          {/* Protected Value */}
          <motion.div variants={itemRise}>
            <TiltCard maxTilt={8} className="h-full">
              <GlassCard className="p-5 h-full" intensity={0.1}>
                <div className="flex items-center justify-between text-xs text-subtle">
                  <span className="font-semibold uppercase tracking-wider">Value Protected</span>
                  <span className="grid size-8 place-items-center rounded-lg bg-cyan-glow/10 text-cyan-glow">
                    <Icon name="shieldCheck" size={17} />
                  </span>
                </div>
                <div className="my-2 font-display text-3xl font-bold tracking-tight text-cyan-glow">
                  {fmtCompactINR(totalValue)}
                </div>
                <div className="text-xs text-muted">Across all indexed retailers</div>
              </GlassCard>
            </TiltCard>
          </motion.div>
        </motion.div>
      )}

      {/* ── Interactive Analytics Section ─────────────────────────────────── */}
      {!purchasesLoading && purchases.length > 0 && (
        <GlassCard className="p-5 sm:p-6" intensity={0.12}>
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="grid size-8 place-items-center rounded-lg bg-cyan-glow/20 text-cyan-glow ring-1 ring-line">
                <Icon name="trendingUp" size={17} />
              </span>
              <div>
                <h3 className="text-sm font-semibold text-fg">Portfolio Health &amp; Analytics</h3>
                <p className="text-[0.68rem] text-subtle">Protection breakdown and retailer distribution</p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowAnalytics(!showAnalytics)}
              className="text-xs font-medium text-muted hover:text-fg transition flex items-center gap-1.5"
            >
              <span>{showAnalytics ? 'Hide charts' : 'Show charts'}</span>
              <Icon name="chevronDown" size={14} className={showAnalytics ? 'rotate-180 transition-transform' : 'transition-transform'} />
            </button>
          </div>

          {showAnalytics && (
            <div className="grid gap-6 lg:grid-cols-3">
              {/* Donut chart: Health Breakdown */}
              <div className="flex flex-col items-center justify-center p-3 rounded-xl border border-line bg-glass text-center">
                <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-subtle">Warranty Status</div>
                <Donut
                  size={160}
                  thickness={14}
                  segments={[
                    { label: 'Safe', value: safeCount, color: '#22d3ee' },
                    { label: 'Expiring Soon', value: expiringSoonCount, color: '#fbbf24' },
                    { label: 'Overdue', value: overdueCount, color: '#fb7185' },
                  ]}
                >
                  <div className="leading-tight">
                    <div className="font-display text-2xl font-bold text-fg">{purchases.length}</div>
                    <div className="text-[0.65rem] text-subtle uppercase tracking-wider">Indexed</div>
                  </div>
                </Donut>
                <div className="mt-3 flex flex-wrap justify-center gap-3 text-[0.7rem] text-subtle">
                  <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-cyan-glow" /> Safe ({safeCount})</span>
                  <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-amber-400" /> Expiring ({expiringSoonCount})</span>
                  <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-rose-400" /> Overdue ({overdueCount})</span>
                </div>
              </div>

              {/* Monthly Spend Activity */}
              <div className="flex flex-col justify-between p-3 rounded-xl border border-line bg-glass">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-subtle">6-Month Purchase Volume</div>
                <div className="py-2">
                  <BarChart data={monthlyData} height={130} format={v => fmtCompactINR(v)} />
                </div>
                <div className="text-center text-[0.68rem] text-subtle">Monthly spending pattern in ₹</div>
              </div>

              {/* Top Retailers Ranked */}
              <div className="flex flex-col justify-between p-3 rounded-xl border border-line bg-glass">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-subtle">Top Retailers Protected</div>
                <div className="py-1">
                  {topRetailers.length > 0 ? (
                    <HBars data={topRetailers} format={v => fmtCompactINR(v)} />
                  ) : (
                    <div className="py-6 text-center text-xs text-subtle">No retailer data available</div>
                  )}
                </div>
                <div className="text-center text-[0.68rem] text-subtle">Value sorted by retailer</div>
              </div>
            </div>
          )}
        </GlassCard>
      )}

      {/* ── Active Coverage Timeline ──────────────────────────────────────── */}
      {!purchasesLoading && purchases.length > 0 && (
        <WarrantyTimeline purchases={purchases} onSelect={onOpenDetail} />
      )}

      {/* ── Search & Filter Toolbar ───────────────────────────────────────── */}
      {!purchasesLoading && purchases.length > 0 && (
        <div className="space-y-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            {/* Search Input */}
            <div className="relative flex-1">
              <Icon name="search" size={17} className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-subtle" />
              <input
                id="search-input"
                type="search"
                value={searchQ}
                onChange={e => setSearchQ(e.target.value)}
                placeholder="Search products, brands, retailers…"
                className="w-full rounded-xl border border-line bg-field py-2.5 pr-4 pl-10 text-sm text-fg placeholder:text-subtle outline-none backdrop-blur-md transition hover:border-line-strong focus:border-violet-glow/70 focus:ring-4 focus:ring-violet-glow/15"
              />
            </div>

            {/* Filter Dropdowns */}
            <div className="flex flex-wrap items-center gap-2">
              <Select value={filterBrand} onChange={e => setFilterBrand(e.target.value)} wrapClassName="min-w-[130px]">
                <option value="">All Brands</option>
                {uniqueBrands.map(b => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </Select>

              <Select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} wrapClassName="min-w-[130px]">
                <option value="">All Status</option>
                <option value="safe">Safe (&gt;30d)</option>
                <option value="expiring">Expiring Soon</option>
                <option value="overdue">Overdue</option>
              </Select>

              <Select value={filterConf} onChange={e => setFilterConf(e.target.value)} wrapClassName="min-w-[130px]">
                <option value="">All Confidence</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </Select>

              <Select value={sortBy} onChange={e => setSortBy(e.target.value)} wrapClassName="min-w-[140px]">
                <option value="date_desc">Newest First</option>
                <option value="date_asc">Oldest First</option>
                <option value="warranty_asc">Expiring Soonest</option>
                <option value="price_desc">Highest Price</option>
                <option value="name_asc">Name A–Z</option>
              </Select>

              {/* View Toggle */}
              <div className="glass flex items-center rounded-xl p-1">
                <button
                  type="button"
                  onClick={() => setViewMode('card')}
                  aria-label="Grid view"
                  className={`grid size-8 place-items-center rounded-lg text-sm transition ${
                    viewMode === 'card' ? 'bg-violet-glow/30 text-fg shadow-sm' : 'text-subtle hover:text-fg'
                  }`}
                >
                  <Icon name="grid" size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('list')}
                  aria-label="List view"
                  className={`grid size-8 place-items-center rounded-lg text-sm transition ${
                    viewMode === 'list' ? 'bg-violet-glow/30 text-fg shadow-sm' : 'text-subtle hover:text-fg'
                  }`}
                >
                  <Icon name="list" size={16} />
                </button>
              </div>
            </div>
          </div>

          {/* Active Filter Chips */}
          {hasActiveFilters && (
            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
              <span className="text-subtle font-medium">Active filters:</span>
              {searchQ && (
                <span className="glass inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-fg">
                  Search: &ldquo;{searchQ}&rdquo;
                  <button type="button" onClick={() => setSearchQ('')} className="text-subtle hover:text-fg">×</button>
                </span>
              )}
              {filterBrand && (
                <span className="glass inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-fg">
                  Brand: {filterBrand}
                  <button type="button" onClick={() => setFilterBrand('')} className="text-subtle hover:text-fg">×</button>
                </span>
              )}
              {filterStatus && (
                <span className="glass inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-fg">
                  Status: {filterStatus}
                  <button type="button" onClick={() => setFilterStatus('')} className="text-subtle hover:text-fg">×</button>
                </span>
              )}
              {filterConf && (
                <span className="glass inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-fg">
                  Confidence: {filterConf}
                  <button type="button" onClick={() => setFilterConf('')} className="text-subtle hover:text-fg">×</button>
                </span>
              )}
              <button
                type="button"
                onClick={clearFilters}
                className="text-cyan-glow hover:underline text-xs font-medium ml-1"
              >
                Clear all
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Results Count ─────────────────────────────────────────────────── */}
      {!purchasesLoading && purchases.length > 0 && (
        <div className="text-xs text-subtle">
          Showing <span className="font-semibold text-fg">{filteredPurchases.length}</span> of {purchases.length} purchases
        </div>
      )}

      {/* ── Purchase Cards Grid / List ────────────────────────────────────── */}
      {purchasesError && (
        <div className="glass-strong rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-200">
          Could not load purchases: {purchasesError}
        </div>
      )}

      {!purchasesLoading && purchases.length === 0 && (
        <EmptyState
          icon="package"
          title="No purchases tracked yet"
          sub="Click 'Scan Inbox' to sync orders from your Gmail account, or upload an invoice PDF."
          action={
            <div className="mt-2 flex flex-wrap gap-3">
              <Button variant="primary" size="md" onClick={onScanInbox} disabled={fetchLoading}>
                {fetchLoading ? <Spinner size={15} /> : 'Scan Inbox Now'}
              </Button>
              <Button variant="secondary" size="md" onClick={() => onNavigate('upload')}>
                Upload Invoice
              </Button>
            </div>
          }
        />
      )}

      {!purchasesLoading && filteredPurchases.length === 0 && purchases.length > 0 && (
        <EmptyState
          icon="search"
          title="No matching purchases found"
          sub="Try adjusting your keywords, brand filter, or status criteria."
          action={
            <Button variant="secondary" size="sm" onClick={clearFilters} className="mt-2">
              Clear Filters
            </Button>
          }
        />
      )}

      {!purchasesLoading && filteredPurchases.length > 0 && viewMode === 'card' && (
        <motion.div
          variants={containerStagger}
          initial="hidden"
          animate="show"
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {filteredPurchases.map(p => (
            <motion.div key={p.id} variants={itemRise}>
              <PurchaseCard purchase={p} onSelect={onOpenDetail} />
            </motion.div>
          ))}
        </motion.div>
      )}

      {!purchasesLoading && filteredPurchases.length > 0 && viewMode === 'list' && (
        <motion.div
          variants={containerStagger}
          initial="hidden"
          animate="show"
          className="flex flex-col gap-2.5"
        >
          {filteredPurchases.map(p => (
            <motion.div key={p.id} variants={itemRise}>
              <PurchaseListItem purchase={p} onSelect={onOpenDetail} />
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  )
}
