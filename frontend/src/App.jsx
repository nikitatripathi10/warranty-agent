import { useState, useEffect, useCallback, useMemo } from 'react'
import { ThemeContext } from './lib/theme-context'
import { useTheme, useToasts, useURLParams } from './lib/hooks'
import Background from './components/Background'
import { TopNav, Sidebar, MobileTopBar, MobileTabBar, Footer } from './components/Shell'
import { ToastStack } from './components/ui'
import FloatingAgentModal from './components/FloatingAgentModal'

import LandingView from './views/LandingView'
import DashboardView from './views/DashboardView'
import DetailView from './views/DetailView'
import AlertsView from './views/AlertsView'
import UploadView from './views/UploadView'
import LookupView from './views/LookupView'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  // ── Auth state ──────────────────────────────────────────────────────────────
  // Drop any leftover sample-workspace session from earlier builds so only real accounts remain.
  const [userId, setUserId] = useState(() => {
    const stored = localStorage.getItem('wrd_user_id') || ''
    if (stored.startsWith('demo-')) {
      localStorage.removeItem('wrd_user_id')
      localStorage.removeItem('wrd_user_email')
      return ''
    }
    return stored
  })
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem('wrd_user_email') || '')
  const isConnected = Boolean(userId && userEmail)

  // ── Theme ───────────────────────────────────────────────────────────────────
  const [theme, toggleTheme] = useTheme()

  // ── Animation FX Palette ────────────────────────────────────────────────────
  const [activePalette, setActivePalette] = useState(() => {
    return localStorage.getItem('wrd_palette') || 'cyberpunk'
  })

  const handleSelectPalette = useCallback((id) => {
    setActivePalette(id)
    localStorage.setItem('wrd_palette', id)
  }, [])

  // ── Toasts ──────────────────────────────────────────────────────────────────
  const [toasts, addToast, removeToast] = useToasts()

  // ── Navigation ──────────────────────────────────────────────────────────────
  const [screen, setScreen] = useState(() => (localStorage.getItem('wrd_user_id') ? 'dashboard' : 'connect'))

  // ── Onboarding ──────────────────────────────────────────────────────────────
  const [onboardStep, setOnboardStep] = useState(0)
  const [hasOnboarded, setHasOnboarded] = useState(() =>
    Boolean(localStorage.getItem('wrd_onboarded'))
  )

  // ── Health ──────────────────────────────────────────────────────────────────
  const [healthStatus, setHealthStatus] = useState('checking')

  // ── Purchases ───────────────────────────────────────────────────────────────
  const [purchases, setPurchases] = useState([])
  const [purchasesLoading, setPurchasesLoading] = useState(false)
  const [purchasesError, setPurchasesError] = useState(null)
  const [selectedPurchase, setSelectedPurchase] = useState(null)

  // ── Edit modal ──────────────────────────────────────────────────────────────
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState({})
  const [editLoading, setEditLoading] = useState(false)
  const [editError, setEditError] = useState(null)

  // ── Alerts ──────────────────────────────────────────────────────────────────
  const [alerts, setAlerts] = useState([])
  const [alertsLoading, setAlertsLoading] = useState(false)

  // ── Upload ──────────────────────────────────────────────────────────────────
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadResult, setUploadResult] = useState(null)
  const [uploadError, setUploadError] = useState(null)

  // ── Fetch emails ─────────────────────────────────────────────────────────────
  const [fetchLoading, setFetchLoading] = useState(false)
  const [fetchResult, setFetchResult] = useState(null)
  const [fetchError, setFetchError] = useState(null)

  // ── Quick lookup ─────────────────────────────────────────────────────────────
  const [testText, setTestText] = useState('')
  const [testLoading, setTestLoading] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testError, setTestError] = useState(null)

  // ── Agent chat ───────────────────────────────────────────────────────────────
  const [agentQuestion, setAgentQuestion] = useState('')
  const [agentAnswer, setAgentAnswer] = useState(null)
  const [agentLoading, setAgentLoading] = useState(false)

  // ── Filters & search ─────────────────────────────────────────────────────────
  const { setParam, getParam } = useURLParams()
  const [viewMode, setViewMode] = useState(() => localStorage.getItem('wrd_view') || 'card')
  const [searchQ, setSearchQ] = useState(() => getParam('q'))
  const [filterBrand, setFilterBrand] = useState(() => getParam('brand'))
  const [filterStatus, setFilterStatus] = useState(() => getParam('status'))
  const [filterConf, setFilterConf] = useState(() => getParam('conf'))
  const [sortBy, setSortBy] = useState(() => getParam('sort') || 'date_desc')

  // ── URL sync ────────────────────────────────────────────────────────────────
  useEffect(() => { setParam('q', searchQ) }, [searchQ, setParam])
  useEffect(() => { setParam('brand', filterBrand) }, [filterBrand, setParam])
  useEffect(() => { setParam('status', filterStatus) }, [filterStatus, setParam])
  useEffect(() => { setParam('conf', filterConf) }, [filterConf, setParam])
  useEffect(() => { setParam('sort', sortBy !== 'date_desc' ? sortBy : '') }, [sortBy, setParam])
  useEffect(() => { localStorage.setItem('wrd_view', viewMode) }, [viewMode])

  // ── Boot & OAuth Handler ────────────────────────────────────────────────────
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const cbUserId = params.get('user_id')
    const cbEmail = params.get('email')
    if (cbUserId && cbEmail) {
      localStorage.setItem('wrd_user_id', cbUserId)
      localStorage.setItem('wrd_user_email', cbEmail)
      setUserId(cbUserId)
      setUserEmail(cbEmail)
      window.history.replaceState({}, '', '/')
      setOnboardStep(1)
    }

    fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) })
      .then(r => (r.ok ? setHealthStatus('ok') : setHealthStatus('error')))
      .catch(() => setHealthStatus('error'))
  }, [])

  useEffect(() => {
    if (isConnected) {
      setScreen('dashboard')
      loadPurchases()
      loadAlerts()
      if (!hasOnboarded) setOnboardStep(1)
    } else {
      setScreen('connect')
    }
  }, [isConnected]) // eslint-disable-line

  // ── API Operations ──────────────────────────────────────────────────────────
  async function loadPurchases() {
    if (!userId) return
    setPurchasesLoading(true)
    setPurchasesError(null)
    try {
      const res = await fetch(`${API_BASE}/purchases?user_id=${encodeURIComponent(userId)}`)
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setPurchases(data.purchases || [])
    } catch (err) {
      setPurchasesError(err.message)
    } finally {
      setPurchasesLoading(false)
    }
  }

  async function loadAlerts() {
    if (!userId) return
    setAlertsLoading(true)
    try {
      const res = await fetch(`${API_BASE}/alerts?user_id=${encodeURIComponent(userId)}&days_ahead=60`)
      const data = await res.json()
      if (res.ok) setAlerts(data.alerts || [])
    } catch {
      /* silent */
    } finally {
      setAlertsLoading(false)
    }
  }

  async function handleFetchEmails() {
    if (!userId) return
    setFetchLoading(true)
    setFetchResult(null)
    setFetchError(null)

    try {
      const res = await fetch(
        `${API_BASE}/ingestion/fetch-emails?user_id=${encodeURIComponent(userId)}&max_results=25`,
        { method: 'POST', signal: AbortSignal.timeout(120000) }
      )
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setFetchResult(data)
      addToast(`Scanned ${data.emails_scanned} emails · ${data.purchases_created} new records saved`, 'success')
      loadPurchases()
      loadAlerts()
      if (onboardStep === 1) setOnboardStep(2)
    } catch (err) {
      setFetchError(err.message)
      addToast(`Scan failed: ${err.message}`, 'error')
    } finally {
      setFetchLoading(false)
    }
  }

  async function handleUpload() {
    if (!uploadFile || !userId) return
    setUploadLoading(true)
    setUploadResult(null)
    setUploadError(null)
    setUploadProgress(15)

    const formData = new FormData()
    formData.append('file', uploadFile)
    formData.append('user_id', userId)

    try {
      const prog = setInterval(() => setUploadProgress(p => Math.min(p + 14, 85)), 500)
      const res = await fetch(`${API_BASE}/ingestion/upload`, {
        method: 'POST',
        body: formData,
        signal: AbortSignal.timeout(60000),
      })
      clearInterval(prog)
      setUploadProgress(100)
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setUploadResult(data)
      addToast('Document processed and saved!', 'success')
      loadPurchases()
      loadAlerts()
    } catch (err) {
      setUploadError(err.message)
      addToast(`Upload failed: ${err.message}`, 'error')
    } finally {
      setUploadLoading(false)
      setTimeout(() => setUploadProgress(0), 1000)
    }
  }

  async function handleExtractionTest() {
    if (!testText.trim()) return
    setTestLoading(true)
    setTestResult(null)
    setTestError(null)

    try {
      const res = await fetch(`${API_BASE}/extraction/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: testText }),
        signal: AbortSignal.timeout(45000),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setTestResult(data)
    } catch (err) {
      setTestError(err.message)
    } finally {
      setTestLoading(false)
    }
  }

  async function handleSaveEdit() {
    setEditLoading(true)
    setEditError(null)

    const body = {}
    if (editForm.product_name !== undefined) body.product_name = editForm.product_name
    if (editForm.brand !== undefined) body.brand = editForm.brand
    if (editForm.retailer !== undefined) body.retailer = editForm.retailer
    if (editForm.purchase_date !== undefined) body.purchase_date = editForm.purchase_date || null
    if (editForm.price !== undefined) body.price = editForm.price ? parseFloat(editForm.price) : null
    if (editForm.warranty_end_date !== undefined) body.warranty_end_date = editForm.warranty_end_date || null
    if (editForm.return_window_end_date !== undefined) body.return_window_end_date = editForm.return_window_end_date || null
    if (editForm.family_member !== undefined) body.family_member = editForm.family_member || null

    try {
      const res = await fetch(
        `${API_BASE}/purchases/${selectedPurchase.id}?user_id=${encodeURIComponent(userId)}`,
        { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
      )
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setSelectedPurchase(data)
      setEditMode(false)
      addToast('Purchase record updated!', 'success')
      loadPurchases()
      loadAlerts()
    } catch (err) {
      setEditError(err.message)
    } finally {
      setEditLoading(false)
    }
  }

  async function handleDeletePurchase(purchaseId) {
    if (!confirm('Delete this purchase record? This cannot be undone.')) return

    try {
      await fetch(
        `${API_BASE}/purchases/${purchaseId}?user_id=${encodeURIComponent(userId)}`,
        { method: 'DELETE' }
      )
      setScreen('dashboard')
      setSelectedPurchase(null)
      addToast('Purchase record deleted.', 'info')
      loadPurchases()
      loadAlerts()
    } catch {
      /* silent */
    }
  }

  async function handleAgentQuery() {
    if (!agentQuestion.trim()) return
    setAgentLoading(true)
    setAgentAnswer(null)

    try {
      const res = await fetch(`${API_BASE}/agent/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, question: agentQuestion }),
        signal: AbortSignal.timeout(30000),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setAgentAnswer(data.answer)
    } catch (err) {
      setAgentAnswer(`Error: ${err.message}`)
    } finally {
      setAgentLoading(false)
    }
  }

  function handleDisconnect() {
    localStorage.removeItem('wrd_user_id')
    localStorage.removeItem('wrd_user_email')
    setUserId('')
    setUserEmail('')
    setPurchases([])
    setAlerts([])
    setSelectedPurchase(null)
    setScreen('connect')
    addToast('Signed out. Connect your Google account to continue.', 'info')
  }

  function handleConnectGmail() {
    window.location.href = `${API_BASE}/auth/gmail/connect`
  }

  function openItemDetail(purchase) {
    setSelectedPurchase(purchase)
    setEditMode(false)
    setEditForm({})
    setEditError(null)
    setAgentQuestion('')
    setAgentAnswer(null)
    setScreen('detail')
  }

  function completeOnboarding() {
    localStorage.setItem('wrd_onboarded', '1')
    setHasOnboarded(true)
    setOnboardStep(3)
  }

  function clearFilters() {
    setSearchQ('')
    setFilterBrand('')
    setFilterStatus('')
    setFilterConf('')
    setSortBy('date_desc')
  }

  const hasActiveFilters = Boolean(
    searchQ || filterBrand || filterStatus || filterConf || sortBy !== 'date_desc'
  )

  return (
    <ThemeContext.Provider value={theme}>
      {/* ── Background: Dynamic Neon Aurora + Beams + Interactive Torch + Particles ── */}
      <Background theme={theme} paletteId={activePalette} />

      {/* ── Toast Notifications ── */}
      <ToastStack toasts={toasts} onRemove={removeToast} />

      {/* ── Landing page for unauthenticated visitors ── */}
      {!isConnected && (
        <div className="min-h-screen flex flex-col justify-between">
          <TopNav
            healthStatus={healthStatus}
            theme={theme}
            onToggleTheme={toggleTheme}
            activePalette={activePalette}
            onSelectPalette={handleSelectPalette}
            onConnect={handleConnectGmail}
          />
          <main className="flex-1">
            <LandingView
              apiBase={API_BASE}
              onboardStep={onboardStep}
              activePalette={activePalette}
            />
          </main>
          <Footer className="px-6" />
        </div>
      )}

      {/* ── Authenticated App Shell ── */}
      {isConnected && (
        <div className="min-h-screen">
          {/* Desktop Left Sidebar */}
          <Sidebar
            screen={screen}
            onNavigate={s => {
              setScreen(s)
              if (s === 'dashboard') loadPurchases()
            }}
            alertCount={alerts.length}
            healthStatus={healthStatus}
            theme={theme}
            onToggleTheme={toggleTheme}
            userEmail={userEmail}
            onSignOut={handleDisconnect}
            activePalette={activePalette}
            onSelectPalette={handleSelectPalette}
          />

          {/* Mobile Top Header */}
          <MobileTopBar
            healthStatus={healthStatus}
            theme={theme}
            onToggleTheme={toggleTheme}
            onSignOut={handleDisconnect}
            activePalette={activePalette}
            onSelectPalette={handleSelectPalette}
            onNavigate={setScreen}
          />

          {/* Main Content Area */}
          <main className="min-h-screen p-4 pb-28 sm:p-6 lg:pl-[19rem] lg:pr-8 lg:pt-8 lg:pb-12">
            <div className="mx-auto max-w-6xl">
              {screen === 'dashboard' && (
                <DashboardView
                  userEmail={userEmail}
                  activePalette={activePalette}
                  purchases={purchases}
                  purchasesLoading={purchasesLoading}
                  purchasesError={purchasesError}
                  alerts={alerts}
                  onAlertsClick={() => setScreen('alerts')}
                  onScanInbox={handleFetchEmails}
                  fetchLoading={fetchLoading}
                  fetchResult={fetchResult}
                  fetchError={fetchError}
                  hasOnboarded={hasOnboarded}
                  onboardStep={onboardStep}
                  onFinishOnboarding={completeOnboarding}
                  onOpenDetail={openItemDetail}
                  onNavigate={setScreen}
                  searchQ={searchQ}
                  setSearchQ={setSearchQ}
                  filterBrand={filterBrand}
                  setFilterBrand={setFilterBrand}
                  filterStatus={filterStatus}
                  setFilterStatus={setFilterStatus}
                  filterConf={filterConf}
                  setFilterConf={setFilterConf}
                  sortBy={sortBy}
                  setSortBy={setSortBy}
                  viewMode={viewMode}
                  setViewMode={setViewMode}
                  clearFilters={clearFilters}
                  hasActiveFilters={hasActiveFilters}
                />
              )}

              {screen === 'detail' && selectedPurchase && (
                <DetailView
                  purchase={selectedPurchase}
                  onBack={() => setScreen('dashboard')}
                  editMode={editMode}
                  setEditMode={setEditMode}
                  editForm={editForm}
                  setEditForm={setEditForm}
                  editLoading={editLoading}
                  editError={editError}
                  onSaveEdit={handleSaveEdit}
                  onDeletePurchase={handleDeletePurchase}
                  agentQuestion={agentQuestion}
                  setAgentQuestion={setAgentQuestion}
                  agentAnswer={agentAnswer}
                  agentLoading={agentLoading}
                  onAgentQuery={handleAgentQuery}
                />
              )}

              {screen === 'alerts' && (
                <AlertsView
                  apiBase={API_BASE}
                  userId={userId}
                  alerts={alerts}
                  alertsLoading={alertsLoading}
                  onRefresh={loadAlerts}
                  purchases={purchases}
                  onSelectPurchase={openItemDetail}
                  addToast={addToast}
                />
              )}

              {screen === 'upload' && (
                <UploadView
                  uploadFile={uploadFile}
                  setUploadFile={setUploadFile}
                  uploadLoading={uploadLoading}
                  uploadProgress={uploadProgress}
                  uploadResult={uploadResult}
                  uploadError={uploadError}
                  onUpload={handleUpload}
                />
              )}

              {screen === 'lookup' && (
                <LookupView
                  testText={testText}
                  setTestText={setTestText}
                  testLoading={testLoading}
                  testResult={testResult}
                  testError={testError}
                  onTestExtraction={handleExtractionTest}
                  isConnected={isConnected}
                  agentQuestion={agentQuestion}
                  setAgentQuestion={setAgentQuestion}
                  agentAnswer={agentAnswer}
                  agentLoading={agentLoading}
                  onAgentQuery={handleAgentQuery}
                />
              )}

              <Footer />
            </div>
          </main>

          {/* Mobile Bottom Tab Bar */}
          <MobileTabBar
            screen={screen}
            onNavigate={s => {
              setScreen(s)
              if (s === 'dashboard') loadPurchases()
            }}
            alertCount={alerts.length}
          />
        </div>
      )}

      {/* Floating assistant (signed-in users only; answers come from the backend) */}
      {isConnected && <FloatingAgentModal apiBase={API_BASE} userId={userId} />}
    </ThemeContext.Provider>
  )
}
