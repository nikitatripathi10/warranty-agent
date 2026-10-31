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

const API_BASE =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' &&
  window.location.hostname !== 'localhost' &&
  window.location.hostname !== '127.0.0.1'
    ? 'https://warranty-agent.onrender.com'
    : 'http://localhost:8000')

const INVALID_PRODUCT_NAMES = new Set([
  '',
  'unnamed product',
  'unknown product',
  'unknown',
  'product',
  'item',
  'none',
  'null',
  'n/a',
  '—',
  '-',
])

const INVALID_VENDORS = new Set([
  '',
  'unknown retailer',
  'unknown',
  'demo electronics',
  'demo',
  'sample',
  'placeholder',
  'none',
  'null',
  'n/a',
  '—',
  '-',
])

function isGenuinePurchase(p) {
  if (!p || typeof p !== 'object') return false
  const name = String(p.product_name || '').trim()
  const retailer = String(p.retailer || '').trim()
  const brand = String(p.brand || '').trim()
  const vendor = retailer || brand

  if (!name || INVALID_PRODUCT_NAMES.has(name.toLowerCase())) return false
  if (!vendor || INVALID_VENDORS.has(vendor.toLowerCase())) return false
  if (retailer && INVALID_VENDORS.has(retailer.toLowerCase())) return false
  if (brand && INVALID_VENDORS.has(brand.toLowerCase())) return false

  const snippet = String(p.warranty_period?.source_snippet || '').toLowerCase()
  if (snippet.includes('demo-2026') || snippet.includes('demo electronics')) return false

  return true
}

function getDeletedPurchaseIds(userId) {
  if (!userId) return new Set()
  try {
    const raw = localStorage.getItem(`wrd_deleted_purchases_${userId}`)
    const arr = raw ? JSON.parse(raw) : []
    return new Set(Array.isArray(arr) ? arr : [])
  } catch {
    return new Set()
  }
}

function addDeletedPurchaseId(userId, purchaseId) {
  if (!userId || !purchaseId) return
  try {
    const set = getDeletedPurchaseIds(userId)
    set.add(purchaseId)
    localStorage.setItem(`wrd_deleted_purchases_${userId}`, JSON.stringify([...set]))
  } catch {
    /* ignore storage errors */
  }
}

async function prepareFileForUpload(file) {
  if (!file || !file.type || !file.type.startsWith('image/')) {
    return file
  }
  return new Promise((resolve) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      URL.revokeObjectURL(url)
      try {
        const maxDim = 1100
        let { width, height } = img
        if (width <= maxDim && height <= maxDim && file.size <= 350 * 1024) {
          resolve(file)
          return
        }
        if (width > maxDim || height > maxDim) {
          const scale = maxDim / Math.max(width, height)
          width = Math.round(width * scale)
          height = Math.round(height * scale)
        }
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        ctx.fillStyle = '#FFFFFF'
        ctx.fillRect(0, 0, width, height)
        ctx.drawImage(img, 0, 0, width, height)
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              resolve(file)
              return
            }
            const baseName = file.name.replace(/\.[^.]+$/, '') || 'document'
            resolve(new File([blob], `${baseName}.jpg`, { type: 'image/jpeg' }))
          },
          'image/jpeg',
          0.85
        )
      } catch {
        resolve(file)
      }
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(file)
    }
    img.src = url
  })
}

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
  const [additionalUploadFile, setAdditionalUploadFile] = useState(null)
  const [additionalWarrantyMonths, setAdditionalWarrantyMonths] = useState('')
  const [additionalWarrantyNotes, setAdditionalWarrantyNotes] = useState('')
  const [selectedUploadPurchaseId, setSelectedUploadPurchaseId] = useState('')
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

    const checkHealth = () => {
      fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(45000) })
        .then(r => (r.ok ? setHealthStatus('ok') : setHealthStatus('error')))
        .catch(() => setHealthStatus('error'))
    }
    checkHealth()
    const keepAlive = setInterval(checkHealth, 240000)
    return () => clearInterval(keepAlive)
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
      const rawList = Array.isArray(data.purchases) ? data.purchases : []
      const deletedIds = getDeletedPurchaseIds(userId)

      const validList = []
      const invalidOrDeletedIds = []

      for (const item of rawList) {
        if (!item?.id) continue
        if (deletedIds.has(item.id) || !isGenuinePurchase(item)) {
          invalidOrDeletedIds.push(item.id)
        } else {
          validList.push(item)
        }
      }

      setPurchases(validList)

      // Permanently purge any unnamed, unknown-retailer, demo, or previously deleted items from DB
      if (invalidOrDeletedIds.length > 0) {
        Promise.allSettled(
          invalidOrDeletedIds.map(id =>
            fetch(`${API_BASE}/purchases/${id}?user_id=${encodeURIComponent(userId)}`, {
              method: 'DELETE',
            })
          )
        )
      }
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
      if (res.ok) {
        const deletedIds = getDeletedPurchaseIds(userId)
        const rawAlerts = Array.isArray(data.alerts) ? data.alerts : []
        const validAlerts = rawAlerts.filter(a => {
          if (!a || deletedIds.has(a.purchase_id)) return false
          const name = String(a.product_name || '').trim()
          const vendor = String(a.retailer || a.brand || '').trim()
          if (!name || INVALID_PRODUCT_NAMES.has(name.toLowerCase())) return false
          if (!vendor || INVALID_VENDORS.has(vendor.toLowerCase())) return false
          return true
        })
        setAlerts(validAlerts)
      }
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
    const cleanMonths = String(additionalWarrantyMonths || '').trim()
    const cleanNotes = String(additionalWarrantyNotes || '').trim()
    const hasManualAdditional = Boolean(cleanMonths || cleanNotes)
    if (!userId || (!uploadFile && !additionalUploadFile && !(selectedUploadPurchaseId && hasManualAdditional))) {
      return
    }

    setUploadLoading(true)
    setUploadResult(null)
    setUploadError(null)
    setUploadProgress(15)

    const prog = setInterval(() => setUploadProgress(p => Math.min(p + 8, 90)), 700)

    try {
      const optimizedStdFile = uploadFile ? await prepareFileForUpload(uploadFile) : null
      const optimizedAddFile = additionalUploadFile ? await prepareFileForUpload(additionalUploadFile) : null
      const prevIds = new Set(purchases.map(p => p.id))

      const parsedManualMonths = cleanMonths ? Math.max(0, parseInt(cleanMonths, 10) || 0) : 0
      const detailParts = []
      if (parsedManualMonths > 0) detailParts.push(`+${parsedManualMonths} months`)
      if (cleanNotes) detailParts.push(cleanNotes)
      if (additionalUploadFile?.name) detailParts.push(`Additional Doc: ${additionalUploadFile.name}`)
      if (uploadFile?.name && additionalUploadFile?.name) {
        detailParts.push(`Manufacturer Doc: ${uploadFile.name}`)
      }
      const clientExtDetails = detailParts.length > 0 ? detailParts.join(' · ') : null

      // Direct manual save to an existing selected product when no file is uploaded
      if (!optimizedStdFile && !optimizedAddFile && selectedUploadPurchaseId && hasManualAdditional) {
        const targetProd = purchases.find(p => p.id === selectedUploadPurchaseId)
        if (!targetProd) throw new Error('Selected product not found.')

        const baseDateStr =
          targetProd.warranty_period?.warranty_end_date ||
          targetProd.purchase_date ||
          new Date().toISOString().slice(0, 10)
        const baseDate = new Date(baseDateStr + 'T00:00:00')
        if (parsedManualMonths > 0) {
          baseDate.setDate(baseDate.getDate() + parsedManualMonths * 30)
        }
        const newEndDate = baseDate.toISOString().slice(0, 10)
        const existingSnippet = (targetProd.warranty_period?.source_snippet || '').trim()
        const updatedSnippet = clientExtDetails
          ? `[Additional Warranty: ${clientExtDetails}]\n${existingSnippet}`.trim()
          : existingSnippet

        const patchRes = await fetch(
          `${API_BASE}/purchases/${selectedUploadPurchaseId}?user_id=${encodeURIComponent(userId)}`,
          {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              warranty_end_date: newEndDate,
              source_snippet: updatedSnippet,
            }),
          }
        )
        const patchedPurchase = await patchRes.json()
        if (!patchRes.ok) throw new Error(patchedPurchase.detail || `HTTP ${patchRes.status}`)

        clearInterval(prog)
        setUploadProgress(100)
        setUploadResult({
          purchase: patchedPurchase,
          extraction: {
            product_name: patchedPurchase.product_name,
            brand: patchedPurchase.brand,
            retailer: patchedPurchase.retailer,
            purchase_date: patchedPurchase.purchase_date,
            price: patchedPurchase.price,
            warranty_period_months: (parsedManualMonths || 12),
            additional_warranty_months: parsedManualMonths || null,
            additional_warranty_details: clientExtDetails,
            confidence: 'high',
            source_snippet: updatedSnippet,
          },
          ocr_used: false,
        })
        setAdditionalWarrantyMonths('')
        setAdditionalWarrantyNotes('')
        addToast('Additional warranty saved and associated with product!', 'success')
        loadPurchases()
        loadAlerts()
        return
      }

      const sendUpload = async () => {
        const formData = new FormData()
        if (optimizedStdFile) {
          formData.append('file', optimizedStdFile)
        } else if (optimizedAddFile) {
          // Also provide under 'file' if only Additional Warranty Document was chosen
          formData.append('file', optimizedAddFile)
        }
        if (optimizedAddFile) {
          formData.append('additional_file', optimizedAddFile)
        }
        formData.append('user_id', userId)
        if (cleanMonths) {
          formData.append('additional_warranty_months', cleanMonths)
        }
        if (cleanNotes) {
          formData.append('additional_warranty_notes', cleanNotes)
        }
        if (selectedUploadPurchaseId) {
          formData.append('purchase_id', selectedUploadPurchaseId)
        }
        return fetch(`${API_BASE}/ingestion/upload`, {
          method: 'POST',
          body: formData,
          signal: AbortSignal.timeout(180000),
        })
      }

      let res
      try {
        res = await sendUpload()
      } catch (firstErr) {
        // Check if backend actually finished saving the record before a proxy timeout
        try {
          const checkRes = await fetch(
            `${API_BASE}/purchases?user_id=${encodeURIComponent(userId)}`,
            { signal: AbortSignal.timeout(20000) }
          )
          if (checkRes.ok) {
            const checkData = await checkRes.json()
            const list = (checkData.purchases || []).filter(isGenuinePurchase)
            const newest = list.find(p => !prevIds.has(p.id) && p.source_type === 'upload')
            if (newest) {
              clearInterval(prog)
              setUploadProgress(100)
              setPurchases(list)
              setUploadResult({
                purchase: newest,
                extraction: {
                  product_name: newest.product_name,
                  brand: newest.brand,
                  retailer: newest.retailer,
                  purchase_date: newest.purchase_date,
                  price: newest.price,
                  confidence: newest.warranty_period?.confidence_score || 'high',
                },
                ocr_used: true,
              })
              addToast('Document processed and saved!', 'success')
              loadAlerts()
              return
            }
          }
        } catch {
          /* ignore check error and retry upload */
        }
        // Retry once after waking backend
        res = await sendUpload()
      }

      clearInterval(prog)
      setUploadProgress(100)
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)

      if (!data?.extraction?.product_name || !isGenuinePurchase(data?.purchase || data?.extraction)) {
        if (data?.purchase?.id) {
          fetch(`${API_BASE}/purchases/${data.purchase.id}?user_id=${encodeURIComponent(userId)}`, {
            method: 'DELETE',
          }).catch(() => {})
        }
        throw new Error(
          'Could not extract valid product and retailer details from this document. Please upload a clear invoice or warranty card.'
        )
      }

      if (clientExtDetails && !data.extraction.additional_warranty_details) {
        data.extraction.additional_warranty_details = clientExtDetails
      }
      if (parsedManualMonths > 0 && !data.extraction.additional_warranty_months) {
        data.extraction.additional_warranty_months = parsedManualMonths
        data.extraction.warranty_period_months =
          (Number(data.extraction.warranty_period_months) || 0) + parsedManualMonths
      }
      if (uploadFile?.name && !data.extraction.manufacturer_doc_name) {
        data.extraction.manufacturer_doc_name = uploadFile.name
      }
      if (additionalUploadFile?.name && !data.extraction.additional_doc_name) {
        data.extraction.additional_doc_name = additionalUploadFile.name
      }

      setFilterConf('')
      setUploadResult(data)
      setAdditionalWarrantyMonths('')
      setAdditionalWarrantyNotes('')
      addToast('Purchase & warranty information saved!', 'success')
      loadPurchases()
      loadAlerts()
    } catch (err) {
      clearInterval(prog)
      const msg =
        err?.name === 'TimeoutError' || /timed out/i.test(err?.message || '')
          ? 'Server took too long to respond. Please click Analyse & Save once more.'
          : err.message
      setUploadError(msg)
      addToast(`Upload failed: ${msg}`, 'error')
    } finally {
      clearInterval(prog)
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
        signal: AbortSignal.timeout(90000),
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
    if (!purchaseId) return

    addDeletedPurchaseId(userId, purchaseId)
    setPurchases(prev => prev.filter(p => p.id !== purchaseId))
    setAlerts(prev => prev.filter(a => a.purchase_id !== purchaseId))
    if (selectedPurchase?.id === purchaseId) {
      setSelectedPurchase(null)
      setScreen('dashboard')
    }
    addToast('Purchase record deleted.', 'info')

    try {
      await fetch(
        `${API_BASE}/purchases/${purchaseId}?user_id=${encodeURIComponent(userId)}`,
        { method: 'DELETE' }
      )
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
              isConnected={false}
              userEmail=""
              onDisconnect={handleDisconnect}
              onboardStep={onboardStep}
              activePalette={activePalette}
              fetchLoading={fetchLoading}
              fetchResult={fetchResult}
              fetchError={fetchError}
              onScanInbox={handleFetchEmails}
              uploadFile={uploadFile}
              setUploadFile={setUploadFile}
              additionalUploadFile={additionalUploadFile}
              setAdditionalUploadFile={setAdditionalUploadFile}
              additionalWarrantyMonths={additionalWarrantyMonths}
              setAdditionalWarrantyMonths={setAdditionalWarrantyMonths}
              additionalWarrantyNotes={additionalWarrantyNotes}
              setAdditionalWarrantyNotes={setAdditionalWarrantyNotes}
              selectedUploadPurchaseId={selectedUploadPurchaseId}
              setSelectedUploadPurchaseId={setSelectedUploadPurchaseId}
              purchases={purchases}
              uploadLoading={uploadLoading}
              uploadProgress={uploadProgress}
              uploadResult={uploadResult}
              uploadError={uploadError}
              onUpload={handleUpload}
              testText={testText}
              setTestText={setTestText}
              testLoading={testLoading}
              testResult={testResult}
              testError={testError}
              onTestExtraction={handleExtractionTest}
            />
          </main>
          <Footer className="px-4" />
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
              {screen === 'connect' && (
                <LandingView
                  apiBase={API_BASE}
                  isConnected={isConnected}
                  userEmail={userEmail}
                  onDisconnect={handleDisconnect}
                  onNavigate={setScreen}
                  onboardStep={onboardStep}
                  activePalette={activePalette}
                  fetchLoading={fetchLoading}
                  fetchResult={fetchResult}
                  fetchError={fetchError}
                  onScanInbox={handleFetchEmails}
                  uploadFile={uploadFile}
                  setUploadFile={setUploadFile}
                  additionalUploadFile={additionalUploadFile}
                  setAdditionalUploadFile={setAdditionalUploadFile}
                  additionalWarrantyMonths={additionalWarrantyMonths}
                  setAdditionalWarrantyMonths={setAdditionalWarrantyMonths}
                  additionalWarrantyNotes={additionalWarrantyNotes}
                  setAdditionalWarrantyNotes={setAdditionalWarrantyNotes}
                  selectedUploadPurchaseId={selectedUploadPurchaseId}
                  setSelectedUploadPurchaseId={setSelectedUploadPurchaseId}
                  purchases={purchases}
                  uploadLoading={uploadLoading}
                  uploadProgress={uploadProgress}
                  uploadResult={uploadResult}
                  uploadError={uploadError}
                  onUpload={handleUpload}
                  testText={testText}
                  setTestText={setTestText}
                  testLoading={testLoading}
                  testResult={testResult}
                  testError={testError}
                  onTestExtraction={handleExtractionTest}
                  purchasesCount={purchases.length}
                  alertsCount={alerts.length}
                />
              )}

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
                  onDeletePurchase={handleDeletePurchase}
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
                  additionalUploadFile={additionalUploadFile}
                  setAdditionalUploadFile={setAdditionalUploadFile}
                  additionalWarrantyMonths={additionalWarrantyMonths}
                  setAdditionalWarrantyMonths={setAdditionalWarrantyMonths}
                  additionalWarrantyNotes={additionalWarrantyNotes}
                  setAdditionalWarrantyNotes={setAdditionalWarrantyNotes}
                  selectedUploadPurchaseId={selectedUploadPurchaseId}
                  setSelectedUploadPurchaseId={setSelectedUploadPurchaseId}
                  purchases={purchases}
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
