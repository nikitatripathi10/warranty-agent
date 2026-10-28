import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { ThemeContext } from './lib/theme-context'
import { useTheme, useToasts, useURLParams } from './lib/hooks'
import Background from './components/Background'
import { TopNav, Sidebar, MobileTopBar, MobileTabBar, Footer } from './components/Shell'
import { ToastStack } from './components/ui'

import LandingView from './views/LandingView'
import DashboardView from './views/DashboardView'
import DetailView from './views/DetailView'
import AlertsView from './views/AlertsView'
import UploadView from './views/UploadView'
import LookupView from './views/LookupView'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const DEMO_PURCHASES = [
  {
    id: 'demo-1',
    product_name: 'Sony WH-1000XM5 Wireless Noise Cancelling Headphones',
    brand: 'Sony',
    retailer: 'Amazon India',
    purchase_date: '2025-10-10',
    price: 29990,
    source_type: 'email',
    family_member: 'Self',
    warranty_period: {
      warranty_end_date: '2026-10-10',
      return_window_end_date: '2025-10-20',
      confidence_score: 'high',
      is_estimated: false,
      source_snippet: '1-year standard brand warranty from date of purchase. 10-day return window.',
    },
  },
  {
    id: 'demo-2',
    product_name: 'Apple MacBook Air M3 (16GB, 512GB SSD) - Starlight',
    brand: 'Apple',
    retailer: 'Croma',
    purchase_date: '2025-11-04',
    price: 114900,
    source_type: 'upload',
    family_member: 'Self',
    warranty_period: {
      warranty_end_date: '2026-11-04',
      return_window_end_date: '2025-11-18',
      confidence_score: 'high',
      is_estimated: false,
      source_snippet: 'Apple 1 Year Limited Warranty with complimentary technical support.',
    },
  },
  {
    id: 'demo-3',
    product_name: 'Dyson V12 Detect Slim Cordless Vacuum Cleaner',
    brand: 'Dyson',
    retailer: 'Flipkart',
    purchase_date: '2025-09-15',
    price: 44900,
    source_type: 'email',
    family_member: 'Home',
    warranty_period: {
      warranty_end_date: '2027-09-15',
      return_window_end_date: '2025-09-25',
      confidence_score: 'high',
      is_estimated: false,
      source_snippet: '2-year official manufacturer warranty. Parts and labor included.',
    },
  },
  {
    id: 'demo-4',
    product_name: 'Instant Pot Duo 7-in-1 Electric Pressure Cooker 6L',
    brand: 'Instant Pot',
    retailer: 'Amazon India',
    purchase_date: '2026-02-12',
    price: 8999,
    source_type: 'email',
    family_member: 'Kitchen',
    warranty_period: {
      warranty_end_date: '2027-02-12',
      return_window_end_date: '2026-02-22',
      confidence_score: 'medium',
      is_estimated: false,
      source_snippet: 'Manufacturer 1-year limited warranty against manufacturing defects.',
    },
  },
  {
    id: 'demo-5',
    product_name: 'Boat Wave Call Smartwatch with Bluetooth Calling',
    brand: 'boAt',
    retailer: 'Blinkit',
    purchase_date: '2026-03-01',
    price: 1499,
    source_type: 'email',
    family_member: 'Sibling',
    warranty_period: {
      warranty_end_date: '2027-03-01',
      return_window_end_date: '2026-03-04',
      confidence_score: 'medium',
      is_estimated: true,
      source_snippet: 'Estimated 1 year standard warranty for personal electronics category.',
    },
  },
]

const DEMO_ALERTS = [
  {
    alert_id: 'alt-1',
    purchase_id: 'demo-1',
    product_name: 'Sony WH-1000XM5 Wireless Noise Cancelling Headphones',
    retailer: 'Amazon India',
    alert_type: 'warranty_expiry',
    fire_date: '2026-10-10',
    days_until: 14,
    is_overdue: false,
  },
  {
    alert_id: 'alt-2',
    purchase_id: 'demo-5',
    product_name: 'Boat Wave Call Smartwatch',
    retailer: 'Blinkit',
    alert_type: 'return_window_expiry',
    fire_date: '2026-03-04',
    days_until: 3,
    is_overdue: false,
  },
]

export default function App() {
  // ── Auth state ──────────────────────────────────────────────────────────────
  const [userId, setUserId] = useState(() => localStorage.getItem('wrd_user_id') || '')
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem('wrd_user_email') || '')
  const isConnected = Boolean(userId && userEmail)

  // ── Theme ───────────────────────────────────────────────────────────────────
  const [theme, toggleTheme] = useTheme()

  // ── Toasts ──────────────────────────────────────────────────────────────────
  const [toasts, addToast, removeToast] = useToasts()

  // ── Navigation ──────────────────────────────────────────────────────────────
  const [screen, setScreen] = useState('connect')

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
    if (userId.startsWith('demo-')) {
      setPurchases(DEMO_PURCHASES)
      return
    }
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
    if (userId.startsWith('demo-')) {
      setAlerts(DEMO_ALERTS)
      return
    }
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

    if (userId.startsWith('demo-')) {
      setTimeout(() => {
        setFetchResult({
          emails_scanned: 18,
          purchases_created: 5,
          purchases_failed: 0,
        })
        setPurchases(DEMO_PURCHASES)
        setAlerts(DEMO_ALERTS)
        addToast('Scanned 18 emails · 5 purchase records saved', 'success')
        setFetchLoading(false)
        if (onboardStep === 1) setOnboardStep(2)
      }, 1200)
      return
    }

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

    if (userId.startsWith('demo-')) {
      const interval = setInterval(() => setUploadProgress(p => Math.min(p + 20, 90)), 300)
      setTimeout(() => {
        clearInterval(interval)
        setUploadProgress(100)
        const mockExtraction = {
          product_name: uploadFile.name.replace(/\.[^/.]+$/, ''),
          brand: 'Samsung',
          retailer: 'Reliance Digital',
          purchase_date: '2026-01-15',
          price: 18499,
          warranty_period_months: 12,
          return_window_days: 7,
          confidence: 'high',
        }
        setUploadResult({ extraction: mockExtraction, ocr_used: true })
        addToast('Invoice processed and indexed!', 'success')
        setUploadLoading(false)
        setPurchases(p => [
          {
            id: `upload-${Date.now()}`,
            product_name: mockExtraction.product_name,
            brand: mockExtraction.brand,
            retailer: mockExtraction.retailer,
            purchase_date: mockExtraction.purchase_date,
            price: mockExtraction.price,
            source_type: 'upload',
            family_member: 'Self',
            warranty_period: {
              warranty_end_date: '2027-01-15',
              return_window_end_date: '2026-01-22',
              confidence_score: 'high',
              is_estimated: false,
              source_snippet: 'Tax Invoice & Customer Warranty Certificate extracted with OCR.',
            },
          },
          ...p,
        ])
      }, 1500)
      return
    }

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

    if (userId.startsWith('demo-')) {
      setTimeout(() => {
        const updated = {
          ...selectedPurchase,
          product_name: editForm.product_name,
          brand: editForm.brand,
          retailer: editForm.retailer,
          purchase_date: editForm.purchase_date,
          price: editForm.price ? parseFloat(editForm.price) : null,
          family_member: editForm.family_member,
          warranty_period: {
            ...selectedPurchase.warranty_period,
            warranty_end_date: editForm.warranty_end_date,
            return_window_end_date: editForm.return_window_end_date,
          },
        }
        setSelectedPurchase(updated)
        setPurchases(ps => ps.map(p => (p.id === updated.id ? updated : p)))
        setEditMode(false)
        setEditLoading(false)
        addToast('Purchase record updated!', 'success')
      }, 500)
      return
    }

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

    if (userId.startsWith('demo-')) {
      setPurchases(ps => ps.filter(p => p.id !== purchaseId))
      setScreen('dashboard')
      setSelectedPurchase(null)
      addToast('Purchase record deleted.', 'info')
      return
    }

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

    if (userId.startsWith('demo-')) {
      setTimeout(() => {
        setAgentAnswer(
          `Based on your portfolio of ${purchases.length} items, your Sony WH-1000XM5 headphones warranty is expiring in 14 days. Your Boat Wave Call smartwatch return window closes on 4 March 2026. The rest of your electronics have healthy manufacturer coverage lasting well into late 2026 and 2027.`
        )
        setAgentLoading(false)
      }, 700)
      return
    }

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
  }

  function handleDemoAccess() {
    const demoId = 'demo-user-1'
    const demoMail = 'kartik.demo@gmail.com'
    localStorage.setItem('wrd_user_id', demoId)
    localStorage.setItem('wrd_user_email', demoMail)
    setUserId(demoId)
    setUserEmail(demoMail)
    setPurchases(DEMO_PURCHASES)
    setAlerts(DEMO_ALERTS)
    setScreen('dashboard')
    addToast('Loaded demo workspace with sample data!', 'success')
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
      {/* ── Background: Aurora + Beams + Particles ── */}
      <Background theme={theme} />

      {/* ── Toast Notifications ── */}
      <ToastStack toasts={toasts} onRemove={removeToast} />

      {/* ── Landing page for unauthenticated visitors ── */}
      {!isConnected && (
        <div className="min-h-screen flex flex-col justify-between">
          <TopNav healthStatus={healthStatus} theme={theme} onToggleTheme={toggleTheme} />
          <main className="flex-1">
            <LandingView
              apiBase={API_BASE}
              onboardStep={onboardStep}
              onDemoAccess={handleDemoAccess}
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
          />

          {/* Mobile Top Header */}
          <MobileTopBar
            healthStatus={healthStatus}
            theme={theme}
            onToggleTheme={toggleTheme}
            onSignOut={handleDisconnect}
          />

          {/* Main Content Area */}
          <main className="min-h-screen p-4 pb-28 sm:p-6 lg:pl-[19rem] lg:pr-8 lg:pt-8 lg:pb-12">
            <div className="mx-auto max-w-6xl">
              {screen === 'dashboard' && (
                <DashboardView
                  userEmail={userEmail}
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
                  alerts={alerts}
                  alertsLoading={alertsLoading}
                  onRefresh={loadAlerts}
                  purchases={purchases}
                  onSelectPurchase={openItemDetail}
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
    </ThemeContext.Provider>
  )
}
