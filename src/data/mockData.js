// RetailIQ mock data — realistic enterprise retail dataset

export const kpiData = {
  revenue: { value: 2847500, change: 12.4, trend: 'up' },
  orders: { value: 18432, change: 8.7, trend: 'up' },
  profit: { value: 428600, change: -2.1, trend: 'down' },
  healthScore: { value: 87, change: 3.2, trend: 'up' },
}

export const revenueTrend = [
  { month: 'Jan', revenue: 2100000, profit: 315000, orders: 14200 },
  { month: 'Feb', revenue: 2250000, profit: 337500, orders: 15100 },
  { month: 'Mar', revenue: 2180000, profit: 327000, orders: 14800 },
  { month: 'Apr', revenue: 2420000, profit: 363000, orders: 16200 },
  { month: 'May', revenue: 2580000, profit: 387000, orders: 17100 },
  { month: 'Jun', revenue: 2650000, profit: 397500, orders: 17600 },
  { month: 'Jul', revenue: 2720000, profit: 408000, orders: 18000 },
  { month: 'Aug', revenue: 2690000, profit: 403500, orders: 17800 },
  { month: 'Sep', revenue: 2780000, profit: 417000, orders: 18200 },
  { month: 'Oct', revenue: 2810000, profit: 421500, orders: 18300 },
  { month: 'Nov', revenue: 2900000, profit: 435000, orders: 18700 },
  { month: 'Dec', revenue: 2847500, profit: 428600, orders: 18432 },
]

export const monthlySales = [
  { month: 'Jan', sales: 14200 },
  { month: 'Feb', sales: 15100 },
  { month: 'Mar', sales: 14800 },
  { month: 'Apr', sales: 16200 },
  { month: 'May', sales: 17100 },
  { month: 'Jun', sales: 17600 },
  { month: 'Jul', sales: 18000 },
  { month: 'Aug', sales: 17800 },
  { month: 'Sep', sales: 18200 },
  { month: 'Oct', sales: 18300 },
  { month: 'Nov', sales: 18700 },
  { month: 'Dec', sales: 18432 },
]

export const inventoryTrend = [
  { week: 'W1', stock: 45000, turnover: 4.2 },
  { week: 'W2', stock: 43500, turnover: 4.5 },
  { week: 'W3', stock: 44200, turnover: 4.3 },
  { week: 'W4', stock: 41800, turnover: 4.8 },
  { week: 'W5', stock: 40500, turnover: 5.1 },
  { week: 'W6', stock: 39800, turnover: 5.3 },
  { week: 'W7', stock: 41200, turnover: 4.9 },
  { week: 'W8', stock: 38900, turnover: 5.5 },
]

export const storeComparison = [
  { store: 'Downtown', revenue: 820000, orders: 5200, growth: 14.2 },
  { store: 'Mall Plaza', revenue: 745000, orders: 4800, growth: 11.8 },
  { store: 'Airport', revenue: 612000, orders: 3900, growth: 8.4 },
  { store: 'Suburban', revenue: 580000, orders: 3600, growth: 6.2 },
  { store: 'Online', revenue: 690500, orders: 932, growth: 22.1 },
]

export const categorySales = [
  { category: 'Personal Care', value: 28, revenue: 797300 },
  { category: 'Electronics', value: 22, revenue: 626450 },
  { category: 'Groceries', value: 20, revenue: 569500 },
  { category: 'Apparel', value: 15, revenue: 427125 },
  { category: 'Home & Living', value: 10, revenue: 284750 },
  { category: 'Others', value: 5, revenue: 142375 },
]

export const topProducts = [
  { id: 1, name: 'Premium Shampoo 500ml', category: 'Personal Care', sales: 8420, revenue: 252600, growth: -8.4, stock: 234 },
  { id: 2, name: 'Wireless Earbuds Pro', category: 'Electronics', sales: 6210, revenue: 310500, growth: 18.2, stock: 89 },
  { id: 3, name: 'Organic Coffee Blend', category: 'Groceries', sales: 5890, revenue: 117800, growth: 12.1, stock: 456 },
  { id: 4, name: 'Running Shoes X200', category: 'Apparel', sales: 4320, revenue: 345600, growth: 5.6, stock: 67 },
  { id: 5, name: 'Smart Watch Series 5', category: 'Electronics', sales: 3980, revenue: 796000, growth: 24.3, stock: 45 },
]

export const criticalAlerts = [
  { id: 1, type: 'critical', title: 'Shampoo sales down 8.4%', description: 'Personal Care category underperforming vs forecast', time: '2h ago' },
  { id: 2, type: 'warning', title: 'Low stock: Wireless Earbuds', description: 'Only 89 units remaining — reorder threshold breached', time: '4h ago' },
  { id: 3, type: 'warning', title: 'Campaign ROI below target', description: 'Summer Sale campaign at 2.1x vs 3.0x target', time: '6h ago' },
  { id: 4, type: 'info', title: 'New supplier contract pending', description: 'BeautyCare Ltd contract renewal due in 14 days', time: '1d ago' },
]

export const recentRecommendations = [
  { id: 1, title: 'Launch targeted shampoo promotion', impact: '+$42K revenue', confidence: 89, priority: 'high' },
  { id: 2, title: 'Reorder Wireless Earbuds Pro', impact: 'Prevent stockout', confidence: 95, priority: 'critical' },
  { id: 3, title: 'Adjust Summer Sale budget allocation', impact: '+15% ROI', confidence: 76, priority: 'medium' },
]

export const products = [
  { id: 'PRD-001', name: 'Premium Shampoo 500ml', category: 'Personal Care', supplier: 'BeautyCare Ltd', price: 29.99, cost: 12.50, stock: 234, status: 'active', margin: 58.3 },
  { id: 'PRD-002', name: 'Wireless Earbuds Pro', category: 'Electronics', supplier: 'TechSound Inc', price: 49.99, cost: 22.00, stock: 89, status: 'low_stock', margin: 56.0 },
  { id: 'PRD-003', name: 'Organic Coffee Blend', category: 'Groceries', supplier: 'GreenBean Co', price: 19.99, cost: 8.50, stock: 456, status: 'active', margin: 57.5 },
  { id: 'PRD-004', name: 'Running Shoes X200', category: 'Apparel', supplier: 'SportFlex', price: 79.99, cost: 35.00, stock: 67, status: 'low_stock', margin: 56.2 },
  { id: 'PRD-005', name: 'Smart Watch Series 5', category: 'Electronics', supplier: 'TechSound Inc', price: 199.99, cost: 95.00, stock: 45, status: 'low_stock', margin: 52.5 },
  { id: 'PRD-006', name: 'Conditioner 400ml', category: 'Personal Care', supplier: 'BeautyCare Ltd', price: 24.99, cost: 10.00, stock: 312, status: 'active', margin: 60.0 },
  { id: 'PRD-007', name: 'Face Moisturizer', category: 'Personal Care', supplier: 'BeautyCare Ltd', price: 34.99, cost: 14.00, stock: 189, status: 'active', margin: 60.0 },
  { id: 'PRD-008', name: 'LED Desk Lamp', category: 'Home & Living', supplier: 'HomeGlow', price: 44.99, cost: 18.00, stock: 156, status: 'active', margin: 60.0 },
  { id: 'PRD-009', name: 'Yoga Mat Premium', category: 'Apparel', supplier: 'SportFlex', price: 39.99, cost: 15.00, stock: 0, status: 'out_of_stock', margin: 62.5 },
  { id: 'PRD-010', name: 'Protein Powder 2kg', category: 'Groceries', supplier: 'NutriMax', price: 54.99, cost: 28.00, stock: 890, status: 'overstock', margin: 49.1 },
  { id: 'PRD-011', name: 'Bluetooth Speaker Mini', category: 'Electronics', supplier: 'TechSound Inc', price: 34.99, cost: 14.50, stock: 234, status: 'active', margin: 58.6 },
  { id: 'PRD-012', name: 'Cotton T-Shirt Pack', category: 'Apparel', supplier: 'FashionHub', price: 29.99, cost: 12.00, stock: 567, status: 'active', margin: 60.0 },
]

export const inventoryData = {
  summary: {
    totalSKUs: 1248,
    totalValue: 4280000,
    turnoverRate: 5.2,
    fillRate: 94.8,
  },
  lowStock: [
    { id: 'PRD-002', name: 'Wireless Earbuds Pro', current: 89, reorder: 150, daysLeft: 4 },
    { id: 'PRD-005', name: 'Smart Watch Series 5', current: 45, reorder: 100, daysLeft: 3 },
    { id: 'PRD-004', name: 'Running Shoes X200', current: 67, reorder: 120, daysLeft: 5 },
  ],
  deadStock: [
    { id: 'PRD-015', name: 'Winter Jacket XL', daysIdle: 120, value: 12400, units: 89 },
    { id: 'PRD-018', name: 'Legacy Phone Case', daysIdle: 95, value: 3200, units: 234 },
    { id: 'PRD-022', name: 'Holiday Gift Set 2024', daysIdle: 87, value: 8900, units: 156 },
  ],
  overstock: [
    { id: 'PRD-010', name: 'Protein Powder 2kg', current: 890, optimal: 400, excess: 490 },
    { id: 'PRD-025', name: 'Bulk Paper Towels', current: 1200, optimal: 600, excess: 600 },
  ],
  reorderSuggestions: [
    { id: 'PRD-002', name: 'Wireless Earbuds Pro', qty: 200, cost: 4400, urgency: 'critical' },
    { id: 'PRD-005', name: 'Smart Watch Series 5', qty: 150, cost: 14250, urgency: 'critical' },
    { id: 'PRD-001', name: 'Premium Shampoo 500ml', qty: 300, cost: 3750, urgency: 'medium' },
  ],
  warehouses: [
    { name: 'Central DC', capacity: 85, skus: 842, value: 2100000 },
    { name: 'East Regional', capacity: 62, skus: 234, value: 980000 },
    { name: 'West Regional', capacity: 71, skus: 172, value: 1200000 },
  ],
  heatmap: [
    { category: 'Personal Care', w1: 78, w2: 82, w3: 75, w4: 68, w5: 72, w6: 65, w7: 70, w8: 62 },
    { category: 'Electronics', w1: 45, w2: 42, w3: 38, w4: 35, w5: 32, w6: 28, w7: 25, w8: 22 },
    { category: 'Groceries', w1: 92, w2: 88, w3: 90, w4: 85, w5: 87, w6: 82, w7: 84, w8: 80 },
    { category: 'Apparel', w1: 55, w2: 58, w3: 52, w4: 48, w5: 50, w6: 45, w7: 42, w8: 40 },
    { category: 'Home & Living', w1: 68, w2: 65, w3: 70, w4: 72, w5: 68, w6: 75, w7: 70, w8: 68 },
  ],
}

export const customers = [
  { id: 'CUS-001', name: 'Sarah Mitchell', email: 'sarah.m@email.com', segment: 'Premium', orders: 47, spent: 8420, lastOrder: '2026-07-15', status: 'active' },
  { id: 'CUS-002', name: 'James Chen', email: 'james.c@email.com', segment: 'Regular', orders: 23, spent: 3210, lastOrder: '2026-07-14', status: 'active' },
  { id: 'CUS-003', name: 'Emily Rodriguez', email: 'emily.r@email.com', segment: 'Premium', orders: 62, spent: 12450, lastOrder: '2026-07-16', status: 'active' },
  { id: 'CUS-004', name: 'Michael Park', email: 'm.park@email.com', segment: 'Regular', orders: 12, spent: 1890, lastOrder: '2026-06-28', status: 'at_risk' },
  { id: 'CUS-005', name: 'Lisa Thompson', email: 'lisa.t@email.com', segment: 'VIP', orders: 89, spent: 24680, lastOrder: '2026-07-16', status: 'active' },
  { id: 'CUS-006', name: 'David Wilson', email: 'd.wilson@email.com', segment: 'Regular', orders: 8, spent: 980, lastOrder: '2026-05-12', status: 'churned' },
  { id: 'CUS-007', name: 'Anna Kowalski', email: 'anna.k@email.com', segment: 'Premium', orders: 34, spent: 6780, lastOrder: '2026-07-13', status: 'active' },
  { id: 'CUS-008', name: 'Robert Singh', email: 'r.singh@email.com', segment: 'Regular', orders: 19, spent: 2450, lastOrder: '2026-07-10', status: 'active' },
]

export const salesAnalytics = {
  daily: [
    { day: 'Mon', revenue: 98000, profit: 14700, orders: 620 },
    { day: 'Tue', revenue: 105000, profit: 15750, orders: 680 },
    { day: 'Wed', revenue: 92000, profit: 13800, orders: 590 },
    { day: 'Thu', revenue: 112000, profit: 16800, orders: 720 },
    { day: 'Fri', revenue: 128000, profit: 19200, orders: 810 },
    { day: 'Sat', revenue: 145000, profit: 21750, orders: 920 },
    { day: 'Sun', revenue: 118000, profit: 17700, orders: 750 },
  ],
  weekly: [
    { week: 'W1', revenue: 720000, profit: 108000, growth: 8.2 },
    { week: 'W2', revenue: 780000, profit: 117000, growth: 8.3 },
    { week: 'W3', revenue: 750000, profit: 112500, growth: -3.8 },
    { week: 'W4', revenue: 820000, profit: 123000, growth: 9.3 },
  ],
  monthly: revenueTrend,
}

export const campaigns = [
  { id: 'CMP-001', name: 'Summer Sale 2026', status: 'active', budget: 85000, spent: 62400, roi: 2.1, impressions: 2400000, conversions: 8420, startDate: '2026-06-01', endDate: '2026-08-31' },
  { id: 'CMP-002', name: 'Back to School', status: 'scheduled', budget: 120000, spent: 0, roi: 0, impressions: 0, conversions: 0, startDate: '2026-08-01', endDate: '2026-09-15' },
  { id: 'CMP-003', name: 'Electronics Flash Sale', status: 'completed', budget: 45000, spent: 44800, roi: 4.2, impressions: 890000, conversions: 3210, startDate: '2026-05-15', endDate: '2026-05-22' },
  { id: 'CMP-004', name: 'Personal Care Bundle', status: 'active', budget: 35000, spent: 28900, roi: 1.8, impressions: 1200000, conversions: 4560, startDate: '2026-07-01', endDate: '2026-07-31' },
  { id: 'CMP-005', name: 'Holiday Preview', status: 'draft', budget: 200000, spent: 0, roi: 0, impressions: 0, conversions: 0, startDate: '2026-11-01', endDate: '2026-12-31' },
]

export const campaignPerformance = [
  { channel: 'Email', spend: 12000, revenue: 48000, roi: 4.0 },
  { channel: 'Social Media', spend: 28000, revenue: 58800, roi: 2.1 },
  { channel: 'Search Ads', spend: 15000, revenue: 52500, roi: 3.5 },
  { channel: 'Display', spend: 7400, revenue: 11100, roi: 1.5 },
]

export const reports = [
  { id: 'RPT-001', title: 'Weekly Executive Summary', type: 'weekly', date: '2026-07-14', status: 'ready', aiSummary: 'Revenue up 8.7% WoW driven by electronics category. Personal care segment requires attention with shampoo sales declining 8.4%.' },
  { id: 'RPT-002', title: 'Monthly Performance Report', type: 'monthly', date: '2026-07-01', status: 'ready', aiSummary: 'Strong month overall with $2.85M revenue. Inventory turnover improved to 5.2x. Three critical stock alerts require immediate action.' },
  { id: 'RPT-003', title: 'Campaign ROI Analysis', type: 'campaign', date: '2026-07-10', status: 'ready', aiSummary: 'Summer Sale underperforming at 2.1x ROI. Recommend reallocating 30% budget to Electronics Flash Sale model.' },
  { id: 'RPT-004', title: 'Inventory Health Report', type: 'inventory', date: '2026-07-12', status: 'ready', aiSummary: 'Fill rate at 94.8%. $24.5K in dead stock identified. Electronics category showing accelerated depletion.' },
  { id: 'RPT-005', title: 'Customer Segmentation Analysis', type: 'customer', date: '2026-07-08', status: 'generating', aiSummary: null },
]

export const decisionHistory = [
  { id: 'DEC-001', question: 'Why are shampoo sales decreasing?', recommendation: 'Launch 15% discount bundle with conditioner', status: 'accepted', outcome: 'Sales recovered 12% within 2 weeks', roi: 340, confidence: 89, date: '2026-07-10', impact: '+$42K revenue' },
  { id: 'DEC-002', question: 'Should we increase earbuds inventory?', recommendation: 'Reorder 200 units immediately', status: 'accepted', outcome: 'Prevented stockout, captured $31K additional revenue', roi: 280, confidence: 95, date: '2026-07-08', impact: 'Stockout prevented' },
  { id: 'DEC-003', question: 'Optimize Summer Sale campaign budget', recommendation: 'Shift 30% budget to social retargeting', status: 'rejected', outcome: 'Original allocation maintained — ROI remained at 2.1x', roi: 0, confidence: 76, date: '2026-07-05', impact: 'No change' },
  { id: 'DEC-004', question: 'Clear dead stock before Q3', recommendation: 'Flash sale on winter items at 40% off', status: 'accepted', outcome: 'Cleared 78% of dead stock, recovered $9.8K', roi: 195, confidence: 82, date: '2026-06-28', impact: '+$9.8K recovered' },
  { id: 'DEC-005', question: 'Expand online channel investment?', recommendation: 'Increase online marketing by 25%', status: 'pending', outcome: null, roi: null, confidence: 71, date: '2026-07-15', impact: 'Est. +$85K revenue' },
]

export const investigationAgents = [
  { id: 'planner', name: 'Planner Agent', icon: 'Brain', task: 'Analyzing query and creating investigation plan', duration: 1800 },
  { id: 'sales', name: 'Sales Agent', icon: 'TrendingDown', task: 'Analyzing sales trends and revenue patterns', duration: 2800 },
  { id: 'inventory', name: 'Inventory Agent', icon: 'Package', task: 'Checking stock levels and turnover rates', duration: 2400 },
  { id: 'campaign', name: 'Campaign Agent', icon: 'Megaphone', task: 'Reviewing active campaigns and marketing spend', duration: 2200 },
  { id: 'pricing', name: 'Pricing Agent', icon: 'DollarSign', task: 'Comparing prices against competitors and market benchmarks', duration: 2600 },
  { id: 'customer', name: 'Customer Agent', icon: 'Users', task: 'Analyzing buying behaviour and customer satisfaction', duration: 2500 },
  { id: 'recommendation', name: 'Recommendation Engine', icon: 'Sparkles', task: 'Combining findings and generating recommendations', duration: 3200 },
]

export const shampooInvestigationResult = {
  rootCause: 'Competitor launched aggressive 20% discount campaign in Personal Care segment. Combined with reduced marketing spend on shampoo category (-35% MoM) and 12% price increase 6 weeks ago.',
  evidence: [
    'Shampoo sales down 8.4% vs last month, 14.2% vs same period last year',
    'Market share dropped from 23% to 19% in Personal Care',
    'Competitor BrandX running 20% off promotion since June 15',
    'Internal marketing spend on shampoo reduced from $12K to $7.8K',
    'Customer satisfaction score dropped from 4.2 to 3.8',
    'Return rate increased from 2.1% to 3.4%',
  ],
  confidence: 89,
  businessImpact: 'Estimated $42K monthly revenue loss if trend continues',
  riskLevel: 'high',
  revenueImpact: -42000,
  inventoryImpact: '234 units at risk of becoming dead stock within 60 days',
  suggestedCampaign: 'Launch "Refresh & Save" bundle — 15% off shampoo + conditioner combo with targeted email to 12K lapsed customers',
  priority: 'high',
  nextSteps: [
    'Approve promotional pricing for 4-week campaign',
    'Increase digital ad spend by $5K/week on shampoo category',
    'Contact supplier for volume discount to protect margins',
    'Deploy customer win-back email sequence',
    'Monitor competitor pricing weekly',
  ],
}

export const simulationDefaults = {
  question: 'What happens if we launch the "Refresh & Save" shampoo bundle campaign?',
  results: {
    sales: { value: '+18%', change: 18, positive: true },
    revenue: { value: '+5%', change: 5, positive: true },
    profit: { value: '-2%', change: -2, positive: false },
    inventory: { value: 'Stockout in 6 days', change: -6, positive: false, isStockout: true },
  },
  recommendation: 'Campaign is recommended. +18% sales lift and +5% revenue growth validated. Reorder 400 units immediately to prevent stockout within 6 days. Pair with supplier volume discount to offset 2% margin compression.',
}

export const promptSuggestions = [
  'Why are shampoo sales decreasing?',
  'Which products need immediate reorder?',
  'How is the Summer Sale campaign performing?',
  'What are our top revenue opportunities?',
  'Analyze customer churn risk this month',
  'Compare store performance across regions',
]

export const notifications = [
  { id: 1, title: 'Critical: Low stock alert', message: 'Wireless Earbuds Pro below reorder threshold', time: '2m ago', read: false },
  { id: 2, title: 'AI Recommendation ready', message: 'New insight on shampoo sales decline', time: '15m ago', read: false },
  { id: 3, title: 'Report generated', message: 'Weekly Executive Summary is ready', time: '1h ago', read: true },
  { id: 4, title: 'Campaign update', message: 'Summer Sale reached 73% of budget', time: '3h ago', read: true },
]

export const formatCurrency = (value) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value)

export const formatNumber = (value) =>
  new Intl.NumberFormat('en-US').format(value)

export const formatPercent = (value) =>
  `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
