// Calls onto the RetailIQ API plus the adapters that reshape entity payloads
// into the shapes the existing UI components consume. Analytics endpoints are
// returned by the backend already in UI shape and need no adaptation.

import { apiDelete, apiGet, apiPatch, apiPost, apiPut, downloadFile } from './client'

const num = (v) => (typeof v === 'number' ? v : Number(v ?? 0))

// ---- adapters --------------------------------------------------------------

export const adaptCustomer = (c) => ({
  id: c.code,
  name: c.name,
  email: c.email,
  segment: c.segment,
  orders: c.total_orders,
  spent: num(c.total_spent),
  lastOrder: c.last_order_date ?? '—',
  status: c.status,
})

export const adaptCampaign = (c) => ({
  id: c.code,
  name: c.name,
  channel: c.channel,
  status: c.status,
  budget: num(c.budget),
  spent: num(c.spent),
  roi: num(c.spent) > 0 ? Number((num(c.revenue) / num(c.spent)).toFixed(1)) : 0,
  impressions: c.impressions,
  conversions: c.conversions,
  startDate: c.start_date ?? '',
  endDate: c.end_date ?? '',
})

export const adaptRecommendation = (r) => ({
  id: r.id,
  code: r.code,
  kind: r.kind,
  title: r.title,
  rationale: r.rationale,
  impact: r.impact,
  confidence: r.confidence,
  priority: r.priority,
  status: r.status,
  evidence: r.evidence,
  revenueImpact: num(r.revenue_impact),
})

export const adaptDecision = (d) => ({
  id: d.code,
  dbId: d.id,
  question: d.question,
  recommendation: d.recommendation_text,
  status: d.status,
  outcome: d.outcome,
  roi: d.roi,
  confidence: d.confidence,
  date: d.decided_on,
  impact: d.impact ?? '—',
})

export const adaptAlert = (a) => ({
  id: a.id,
  type: a.severity,
  title: a.title,
  description: a.message,
  message: a.message,
  category: a.category,
  read: a.is_read,
  time: new Date(a.occurred_at).toLocaleString([], {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  }),
})

export const adaptReport = (r) => ({
  id: r.code,
  dbId: r.id,
  title: r.title,
  type: r.kind,
  date: r.period_end ?? r.created_at?.slice(0, 10),
  status: r.status,
  aiSummary: r.summary,
})

const adaptPeriod = (rows, key) =>
  rows.map((r) => ({
    [key]: r.label,
    revenue: r.revenue,
    profit: r.profit,
    orders: r.orders,
    growth: r.growth,
  }))

// ---- auth ------------------------------------------------------------------

export const login = (email, password) => apiPost('/auth/login', { email, password })
export const getMe = () => apiGet('/auth/me')
export const updateMe = (payload) => apiPatch('/auth/me', payload)
export const changePassword = (payload) => apiPost('/auth/me/password', payload)
export const getPreferences = () => apiGet('/auth/me/preferences')
export const savePreferences = (payload) => apiPut('/auth/me/preferences', payload)

// ---- analytics -------------------------------------------------------------

export const getKpis = () => apiGet('/analytics/kpis')
export const getRevenueTrend = () => apiGet('/analytics/revenue-trend')
export const getMonthlySales = () => apiGet('/analytics/monthly-sales')
export const getInventoryTrend = () => apiGet('/analytics/inventory-trend')
export const getStoreComparison = () => apiGet('/analytics/store-comparison')
export const getCategorySales = () => apiGet('/analytics/category-sales')
export const getTopProducts = () => apiGet('/analytics/top-products')
export const getProducts = () => apiGet('/analytics/products-overview')
export const getInventoryOverview = () => apiGet('/analytics/inventory-overview')
export const getCampaignPerformance = () => apiGet('/analytics/campaign-performance')

export const getCustomers = async () => (await apiGet('/customers')).map(adaptCustomer)
export const getCampaigns = async () => (await apiGet('/campaigns')).map(adaptCampaign)
export const getStores = () => apiGet('/stores')
export const getInventoryRows = () => apiGet('/inventory')
export const getCategoriesList = async () => {
  const rows = await apiGet('/products?limit=200')
  const map = new Map()
  rows.forEach((p) => p.category && map.set(p.category.id, p.category.name))
  return [...map].map(([id, name]) => ({ id, name }))
}

export const getSalesAnalytics = async () => {
  const [daily, weekly, monthly] = await Promise.all([
    apiGet('/analytics/sales?period=daily'),
    apiGet('/analytics/sales?period=weekly'),
    apiGet('/analytics/sales?period=monthly'),
  ])
  return {
    daily: adaptPeriod(daily, 'day'),
    weekly: adaptPeriod(weekly, 'week'),
    monthly: adaptPeriod(monthly, 'month'),
  }
}

// ---- intelligence ----------------------------------------------------------

export const getRecommendations = async () =>
  (await apiGet('/recommendations')).map(adaptRecommendation)
export const generateRecommendations = async () =>
  (await apiPost('/recommendations/generate')).map(adaptRecommendation)
export const actOnRecommendation = async (id, status, note) =>
  adaptRecommendation(await apiPost(`/recommendations/${id}/action`, { status, note }))

export const getDecisions = async () => (await apiGet('/decisions')).map(adaptDecision)

export const getAlerts = async () => (await apiGet('/alerts')).map(adaptAlert)
export const evaluateAlerts = async () => (await apiPost('/alerts/evaluate')).map(adaptAlert)
export const markAlertRead = (id) => apiPost(`/alerts/${id}/read`)
export const markAllAlertsRead = () => apiPost('/alerts/read-all')

export const getReports = async () => (await apiGet('/reports')).map(adaptReport)
export const generateReport = async (kind) =>
  adaptReport(await apiPost('/reports/generate', { kind }))
export const downloadReport = (dbId, code, fmt = 'csv') =>
  downloadFile(`/reports/${dbId}/download?fmt=${fmt}`, `${code}.${fmt}`)

export const runSimulation = (payload) => apiPost('/simulations/run', payload)
export const getSimulations = () => apiGet('/simulations')

// ---- copilot + RAG ---------------------------------------------------------

export const askCopilot = (question, conversationId) =>
  apiPost('/copilot/query', { question, conversation_id: conversationId ?? null }, { timeoutMs: 120000 })
export const getConversations = () => apiGet('/copilot/conversations')
export const getConversation = (id) => apiGet(`/copilot/conversations/${id}`)
export const deleteConversation = (id) => apiDelete(`/copilot/conversations/${id}`)
export const getDocuments = () => apiGet('/copilot/documents')
export const createDocument = (payload) => apiPost('/copilot/documents', payload)
export const deleteDocument = (id) => apiDelete(`/copilot/documents/${id}`)
export const searchKnowledge = (q) => apiGet(`/copilot/search?q=${encodeURIComponent(q)}`)
export const getKnowledgeStats = () => apiGet('/copilot/knowledge-stats')

// ---- operations ------------------------------------------------------------

export const createProduct = (payload) => apiPost('/products', payload)
export const updateProduct = (id, payload) => apiPatch(`/products/${id}`, payload)
export const deleteProduct = (id) => apiDelete(`/products/${id}`)
export const adjustStock = (payload) => apiPost('/inventory/adjust', payload)
export const createPurchaseOrder = (payload) => apiPost('/purchase-orders', payload)
export const getPurchaseOrders = () => apiGet('/purchase-orders')
export const receivePurchaseOrder = (id) => apiPost(`/purchase-orders/${id}/receive`)
export const getStockMovements = (productId) =>
  apiGet(`/stock-movements${productId ? `?product_id=${productId}` : ''}`)

// ---- bulk dashboard load ---------------------------------------------------

export async function loadRetailData() {
  const [
    kpi, revenueTrend, monthlySales, inventoryTrend, topProducts,
    products, inventory, storeComparison, categorySales,
    customers, campaigns, campaignPerformance, salesAnalytics,
    recommendations, decisions, alerts, reports,
  ] = await Promise.all([
    getKpis(), getRevenueTrend(), getMonthlySales(), getInventoryTrend(),
    getTopProducts(), getProducts(), getInventoryOverview(),
    getStoreComparison(), getCategorySales(), getCustomers(), getCampaigns(),
    getCampaignPerformance(), getSalesAnalytics(),
    getRecommendations(), getDecisions(), getAlerts(), getReports(),
  ])
  return {
    kpi, revenueTrend, monthlySales, inventoryTrend, topProducts,
    products, inventory, storeComparison, categorySales,
    customers, campaigns, campaignPerformance, salesAnalytics,
    recommendations, decisions, alerts, reports,
  }
}
