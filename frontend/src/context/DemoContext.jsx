import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import * as api from '../api/retail'
import { simulationDefaults } from '../data/mockData'

// Application data layer. Every dataset here comes from the FastAPI backend;
// nothing is mocked. The provider is mounted inside the auth guard so requests
// always carry a token.
const DemoContext = createContext(null)

let toastId = 0

// Zeroed shapes so components can render during the first load without
// null-guards on every field.
const EMPTY_KPI = {
  revenue: { value: 0, change: 0, trend: 'up' },
  orders: { value: 0, change: 0, trend: 'up' },
  profit: { value: 0, change: 0, trend: 'up' },
  healthScore: { value: 0, change: 0, trend: 'up' },
}

const EMPTY_INVENTORY = {
  summary: { totalSKUs: 0, totalValue: 0, turnoverRate: 0, fillRate: 0 },
  lowStock: [], deadStock: [], overstock: [], reorderSuggestions: [],
  warehouses: [], heatmap: [],
}

export function DemoProvider({ children }) {
  const [kpi, setKpi] = useState(EMPTY_KPI)
  const [revenueTrend, setRevenueTrend] = useState([])
  const [monthlySales, setMonthlySales] = useState([])
  const [inventoryTrend, setInventoryTrend] = useState([])
  const [topProducts, setTopProducts] = useState([])
  const [products, setProducts] = useState([])
  const [inventory, setInventory] = useState(EMPTY_INVENTORY)
  const [storeComparison, setStoreComparison] = useState([])
  const [categorySales, setCategorySales] = useState([])
  const [customers, setCustomers] = useState([])
  const [campaigns, setCampaigns] = useState([])
  const [campaignPerformance, setCampaignPerformance] = useState([])
  const [salesAnalytics, setSalesAnalytics] = useState({ daily: [], weekly: [], monthly: [] })
  const [recommendations, setRecommendations] = useState([])
  const [decisions, setDecisions] = useState([])
  const [alerts, setAlerts] = useState([])
  const [reports, setReports] = useState([])

  const [toasts, setToasts] = useState([])
  const [dataLoading, setDataLoading] = useState(true)
  const [dataError, setDataError] = useState(null)
  const [simulationPhase, setSimulationPhase] = useState('idle')
  const [simulationResult, setSimulationResult] = useState(null)
  const mounted = useRef(true)

  // StrictMode mounts, unmounts and remounts in development. The ref must be
  // re-armed on mount, otherwise it stays false after the simulated unmount and
  // every subsequent setState is discarded — leaving the UI stuck on "loading".
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  // ---- toasts --------------------------------------------------------

  const pushToast = useCallback((toast) => {
    const id = ++toastId
    setToasts((prev) => [...prev, { id, ...toast }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), toast.duration || 5000)
  }, [])

  // ---- load ----------------------------------------------------------

  const refreshData = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setDataLoading(true)
    try {
      const d = await api.loadRetailData()
      if (!mounted.current) return
      setKpi(d.kpi); setRevenueTrend(d.revenueTrend); setMonthlySales(d.monthlySales)
      setInventoryTrend(d.inventoryTrend); setTopProducts(d.topProducts)
      setProducts(d.products); setInventory(d.inventory)
      setStoreComparison(d.storeComparison); setCategorySales(d.categorySales)
      setCustomers(d.customers); setCampaigns(d.campaigns)
      setCampaignPerformance(d.campaignPerformance); setSalesAnalytics(d.salesAnalytics)
      setRecommendations(d.recommendations); setDecisions(d.decisions)
      setAlerts(d.alerts); setReports(d.reports)
      setDataError(null)
    } catch (err) {
      if (mounted.current) setDataError(err.message || 'Unable to reach the RetailIQ API')
    } finally {
      if (mounted.current) setDataLoading(false)
    }
  }, [])

  useEffect(() => { refreshData() }, [refreshData])

  // ---- notifications -------------------------------------------------

  const notifications = useMemo(
    () => alerts.map((a) => ({
      id: a.id, title: a.title, message: a.message, time: a.time, read: a.read, type: a.type,
    })),
    [alerts],
  )
  const criticalAlerts = useMemo(
    () => alerts.filter((a) => a.type === 'critical' || a.type === 'warning'),
    [alerts],
  )
  const recentRecommendations = useMemo(
    () => recommendations.filter((r) => r.status === 'pending').slice(0, 3),
    [recommendations],
  )

  const markNotificationRead = useCallback(async (id) => {
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, read: true } : a)))
    try { await api.markAlertRead(id) } catch { /* optimistic; refreshed next load */ }
  }, [])

  const markAllNotificationsRead = useCallback(async () => {
    setAlerts((prev) => prev.map((a) => ({ ...a, read: true })))
    try { await api.markAllAlertsRead() } catch { /* optimistic */ }
  }, [])

  const addNotification = useCallback((n) => {
    pushToast({ title: n.title, message: n.message, type: n.type || 'info' })
  }, [pushToast])

  // ---- actions -------------------------------------------------------

  const acceptRecommendation = useCallback(async (id, status = 'accepted', note) => {
    const updated = await api.actOnRecommendation(id, status, note)
    setRecommendations((prev) => prev.map((r) => (r.id === id ? updated : r)))
    const [freshDecisions, freshRecs] = await Promise.all([
      api.getDecisions(), api.getRecommendations(),
    ])
    setDecisions(freshDecisions)
    setRecommendations(freshRecs)
    pushToast({
      title: status === 'accepted' ? 'Recommendation accepted' : 'Recommendation dismissed',
      message: updated.title,
      type: status === 'accepted' ? 'success' : 'info',
    })
    return updated
  }, [pushToast])

  const regenerateRecommendations = useCallback(async () => {
    const fresh = await api.generateRecommendations()
    setRecommendations(fresh)
    pushToast({ title: 'Recommendations refreshed',
      message: `${fresh.length} open recommendation(s) from live data`, type: 'success' })
    return fresh
  }, [pushToast])

  const runSimulation = useCallback(async (scenario) => {
    setSimulationPhase('running')
    pushToast({ title: 'Simulation started', message: 'Modelling scenario against live sales…', type: 'info' })
    try {
      const payload = scenario ?? {
        name: 'Refresh & Save bundle', discount_pct: 15,
        duration_days: 28, category: 'Personal Care', extra_spend: 0,
      }
      const result = await api.runSimulation(payload)
      if (!mounted.current) return null
      setSimulationResult(result)
      setSimulationPhase('complete')
      pushToast({ title: 'Simulation complete', message: result.summary?.slice(0, 120), type: 'success' })
      await refreshData({ silent: true })
      return result
    } catch (err) {
      if (mounted.current) setSimulationPhase('idle')
      pushToast({ title: 'Simulation failed', message: err.message, type: 'error' })
      throw err
    }
  }, [pushToast, refreshData])

  const generateReport = useCallback(async (kind = 'weekly') => {
    pushToast({ title: 'Generating report', message: 'Compiling from live business data…', type: 'info' })
    const report = await api.generateReport(kind)
    setReports((prev) => [{ ...report, isNew: true }, ...prev])
    pushToast({
      title: report.status === 'ready' ? 'Report ready' : 'Report failed',
      message: report.title,
      type: report.status === 'ready' ? 'success' : 'error',
    })
    return report
  }, [pushToast])

  const refreshAlerts = useCallback(async () => {
    const fresh = await api.evaluateAlerts()
    setAlerts(fresh)
    pushToast({ title: 'Alerts re-evaluated', message: `${fresh.length} active alert(s)`, type: 'info' })
    return fresh
  }, [pushToast])

  const value = {
    // datasets
    kpi, revenueTrend, monthlySales, inventoryTrend, topProducts,
    products, inventory, storeComparison, categorySales,
    customers, campaigns, campaignPerformance, salesAnalytics,
    recommendations, decisions, reports, alerts,
    notifications, criticalAlerts, recentRecommendations,
    simulationDefaults,
    // state
    toasts, dataLoading, dataError, simulationPhase, simulationResult,
    // actions
    refreshData, pushToast, addNotification,
    markNotificationRead, markAllNotificationsRead,
    acceptRecommendation, regenerateRecommendations,
    runSimulation, generateReport, refreshAlerts,
  }

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
}

export function useDemo() {
  const ctx = useContext(DemoContext)
  if (!ctx) throw new Error('useDemo must be used within DemoProvider')
  return ctx
}
