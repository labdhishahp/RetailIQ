import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import {
  kpiData as initialKpi,
  revenueTrend as initialRevenueTrend,
  monthlySales as initialMonthlySales,
  inventoryTrend as initialInventoryTrend,
  topProducts as initialTopProducts,
  criticalAlerts as initialAlerts,
  recentRecommendations as initialRecommendations,
  inventoryData as initialInventory,
  notifications as initialNotifications,
  decisionHistory as initialDecisions,
  reports as initialReports,
  products as initialProducts,
  shampooInvestigationResult,
} from '../data/mockData'

const DemoContext = createContext(null)

let notificationId = 100
let decisionId = 100
let reportId = 100

export function DemoProvider({ children }) {
  const [kpi, setKpi] = useState(initialKpi)
  const [revenueTrend, setRevenueTrend] = useState(initialRevenueTrend)
  const [monthlySales, setMonthlySales] = useState(initialMonthlySales)
  const [inventoryTrend, setInventoryTrend] = useState(initialInventoryTrend)
  const [topProducts, setTopProducts] = useState(initialTopProducts)
  const [criticalAlerts, setCriticalAlerts] = useState(initialAlerts)
  const [recentRecommendations, setRecentRecommendations] = useState(initialRecommendations)
  const [inventory, setInventory] = useState(initialInventory)
  const [products, setProducts] = useState(initialProducts)
  const [notifications, setNotifications] = useState(initialNotifications)
  const [decisions, setDecisions] = useState(initialDecisions)
  const [reports, setReports] = useState(initialReports)
  const [toasts, setToasts] = useState([])
  const [simulationPhase, setSimulationPhase] = useState('idle') // idle | running | complete
  const [investigationComplete, setInvestigationComplete] = useState(false)
  const livePulseRef = useRef(null)

  const pushToast = useCallback((toast) => {
    const id = ++notificationId
    setToasts((prev) => [...prev, { id, ...toast }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, toast.duration || 5000)
  }, [])

  const addNotification = useCallback((notification) => {
    const id = ++notificationId
    setNotifications((prev) => [{ id, read: false, ...notification }, ...prev])
    pushToast({
      title: notification.title,
      message: notification.message,
      type: notification.type || 'info',
    })
  }, [pushToast])

  const markNotificationRead = useCallback((id) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    )
  }, [])

  const markAllNotificationsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }, [])

  const onInvestigationComplete = useCallback(() => {
    setInvestigationComplete(true)
    addNotification({
      title: 'AI Investigation Complete',
      message: 'Shampoo sales analysis ready — review recommendation in Copilot',
      time: 'Just now',
      type: 'success',
    })
  }, [addNotification])

  const runSimulation = useCallback(() => {
    if (simulationPhase === 'running') return
    setSimulationPhase('running')

    addNotification({
      title: 'Simulation Started',
      message: 'Modeling "Refresh & Save" bundle campaign impact...',
      time: 'Just now',
      type: 'info',
    })

    setTimeout(() => {
      setKpi((prev) => ({
        revenue: { value: Math.round(prev.revenue.value * 1.05), change: 5.0, trend: 'up' },
        orders: { value: Math.round(prev.orders.value * 1.18), change: 18.0, trend: 'up' },
        profit: { value: Math.round(prev.profit.value * 0.98), change: -2.0, trend: 'down' },
        healthScore: { value: 91, change: 4.6, trend: 'up' },
      }))

      setRevenueTrend((prev) => {
        const updated = [...prev]
        const last = { ...updated[updated.length - 1] }
        last.revenue = Math.round(last.revenue * 1.05)
        last.profit = Math.round(last.profit * 0.98)
        last.orders = Math.round(last.orders * 1.18)
        updated[updated.length - 1] = last
        return updated
      })

      setMonthlySales((prev) => {
        const updated = [...prev]
        const last = { ...updated[updated.length - 1] }
        last.sales = Math.round(last.sales * 1.18)
        updated[updated.length - 1] = last
        return updated
      })

      setInventoryTrend((prev) => {
        const updated = [...prev]
        const last = { ...updated[updated.length - 1] }
        last.stock = Math.round(last.stock * 0.76)
        last.turnover = Math.round(last.turnover * 1.15 * 10) / 10
        updated[updated.length - 1] = last
        return updated
      })

      setTopProducts((prev) =>
        prev.map((p) =>
          p.name.includes('Shampoo')
            ? { ...p, growth: 18.0, sales: Math.round(p.sales * 1.18), revenue: Math.round(p.revenue * 1.05), stock: 98 }
            : p
        )
      )

      setProducts((prev) =>
        prev.map((p) =>
          p.id === 'PRD-001'
            ? { ...p, stock: 98, status: 'low_stock' }
            : p
        )
      )

      setInventory((prev) => {
        const shampooLowStock = {
          id: 'PRD-001',
          name: 'Premium Shampoo 500ml',
          current: 98,
          reorder: 150,
          daysLeft: 6,
        }
        const existingLow = prev.lowStock.filter((i) => i.id !== 'PRD-001')
        return {
          ...prev,
          summary: { ...prev.summary, fillRate: 92.4, turnoverRate: 5.8 },
          lowStock: [shampooLowStock, ...existingLow],
          reorderSuggestions: prev.reorderSuggestions.map((r) =>
            r.id === 'PRD-001' ? { ...r, urgency: 'critical', qty: 400 } : r
          ),
        }
      })

      setCriticalAlerts((prev) => [
        {
          id: ++notificationId,
          type: 'warning',
          title: 'Shampoo stockout projected in 6 days',
          description: 'Campaign simulation shows accelerated depletion — reorder recommended',
          time: 'Just now',
        },
        ...prev,
      ])

      setRecentRecommendations((prev) => [
        {
          id: ++notificationId,
          title: 'Execute "Refresh & Save" bundle campaign',
          impact: '+18% sales · +5% revenue',
          confidence: 89,
          priority: 'high',
        },
        ...prev.slice(0, 2),
      ])

      const newDecision = {
        id: `DEC-${++decisionId}`,
        question: 'Why are shampoo sales decreasing?',
        recommendation: shampooInvestigationResult.suggestedCampaign,
        status: 'accepted',
        outcome: 'Simulation validated: +18% sales, +5% revenue, stockout in 6 days without reorder',
        roi: 340,
        confidence: 89,
        date: new Date().toISOString().split('T')[0],
        impact: '+18% sales · +5% revenue',
        isNew: true,
      }
      setDecisions((prev) => [newDecision, ...prev])

      const newReport = {
        id: `RPT-${++reportId}`,
        title: 'Shampoo Campaign Simulation Report',
        type: 'simulation',
        date: new Date().toISOString().split('T')[0],
        status: 'generating',
        aiSummary: null,
        isNew: true,
      }
      setReports((prev) => [newReport, ...prev])

      addNotification({
        title: 'Simulation Complete',
        message: 'Sales +18% · Revenue +5% · Profit -2% · Stockout in 6 days',
        time: 'Just now',
        type: 'success',
      })

      addNotification({
        title: 'Inventory Alert',
        message: 'Premium Shampoo 500ml projected stockout in 6 days',
        time: 'Just now',
        type: 'warning',
      })

      setTimeout(() => {
        setReports((prev) =>
          prev.map((r) =>
            r.id === newReport.id
              ? {
                  ...r,
                  status: 'ready',
                  aiSummary:
                    'Campaign simulation confirms +18% sales lift and +5% revenue growth. Margin compression of 2% offset by volume gains. Shampoo inventory will reach stockout in 6 days — immediate reorder of 400 units recommended.',
                }
              : r
          )
        )
        addNotification({
          title: 'Report Generated',
          message: 'Shampoo Campaign Simulation Report is ready to download',
          time: 'Just now',
          type: 'info',
        })
      }, 3500)

      setSimulationPhase('complete')
    }, 2800)
  }, [simulationPhase, addNotification])

  useEffect(() => {
    livePulseRef.current = setInterval(() => {
      setKpi((prev) => ({
        ...prev,
        revenue: {
          ...prev.revenue,
          value: prev.revenue.value + Math.floor(Math.random() * 800 + 200),
        },
        orders: {
          ...prev.orders,
          value: prev.orders.value + Math.floor(Math.random() * 3 + 1),
        },
      }))
    }, 12000)

    return () => clearInterval(livePulseRef.current)
  }, [])

  const value = {
    kpi,
    revenueTrend,
    monthlySales,
    inventoryTrend,
    topProducts,
    criticalAlerts,
    recentRecommendations,
    inventory,
    products,
    notifications,
    decisions,
    reports,
    toasts,
    simulationPhase,
    investigationComplete,
    addNotification,
    markNotificationRead,
    markAllNotificationsRead,
    onInvestigationComplete,
    runSimulation,
    pushToast,
  }

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
}

export function useDemo() {
  const ctx = useContext(DemoContext)
  if (!ctx) throw new Error('useDemo must be used within DemoProvider')
  return ctx
}
