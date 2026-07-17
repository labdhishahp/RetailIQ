import { DollarSign, ShoppingCart, TrendingUp, Activity, AlertTriangle, ArrowRight, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import PageHeader from '../components/ui/PageHeader'
import KpiCard from '../components/ui/KpiCard'
import Card from '../components/ui/Card'
import StatusChip from '../components/ui/StatusChip'
import Button from '../components/ui/Button'
import ChartCard from '../components/charts/ChartCard'
import RevenueTrendChart from '../components/charts/RevenueTrendChart'
import BarChartComponent from '../components/charts/BarChartComponent'
import PieChartComponent from '../components/charts/PieChartComponent'
import GaugeChart from '../components/charts/GaugeChart'
import LineChartComponent from '../components/charts/LineChartComponent'
import {
  kpiData, revenueTrend, monthlySales, inventoryTrend, storeComparison,
  categorySales, topProducts, criticalAlerts, recentRecommendations, formatCurrency, formatPercent,
} from '../data/mockData'

export default function Dashboard() {
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader
        title="Executive Dashboard"
        subtitle="Real-time business intelligence overview"
        actions={
          <Button icon={Sparkles} onClick={() => navigate('/copilot')}>
            Ask AI Copilot
          </Button>
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <KpiCard title="Total Revenue" value={kpiData.revenue.value} change={kpiData.revenue.change} trend={kpiData.revenue.trend} icon={DollarSign} delay={0} />
        <KpiCard title="Total Orders" value={kpiData.orders.value} change={kpiData.orders.change} trend={kpiData.orders.trend} icon={ShoppingCart} format="number" delay={0.05} />
        <KpiCard title="Net Profit" value={kpiData.profit.value} change={kpiData.profit.change} trend={kpiData.profit.trend} icon={TrendingUp} delay={0.1} />
        <KpiCard title="Business Health" value={kpiData.healthScore.value} change={kpiData.healthScore.change} trend={kpiData.healthScore.trend} icon={Activity} format="percent" delay={0.15} />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="lg:col-span-2">
          <ChartCard title="Revenue Trend" subtitle="Monthly revenue and profit performance">
            <RevenueTrendChart data={revenueTrend} />
          </ChartCard>
        </div>
        <ChartCard title="Business Health" subtitle="Overall performance score">
          <GaugeChart value={kpiData.healthScore.value} />
        </ChartCard>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <ChartCard title="Monthly Sales" subtitle="Order volume trend">
          <LineChartComponent data={monthlySales} lines={[{ key: 'sales', color: '#2563EB', name: 'Orders' }]} />
        </ChartCard>
        <ChartCard title="Store Comparison" subtitle="Revenue by location">
          <BarChartComponent data={storeComparison} dataKey="revenue" xKey="store" />
        </ChartCard>
        <ChartCard title="Category Sales" subtitle="Revenue distribution">
          <PieChartComponent data={categorySales} />
        </ChartCard>
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Inventory Trend */}
        <ChartCard title="Inventory Trend" subtitle="Stock levels over time">
          <LineChartComponent
            data={inventoryTrend}
            xKey="week"
            lines={[
              { key: 'stock', color: '#2563EB', name: 'Stock Level' },
              { key: 'turnover', color: '#22C55E', name: 'Turnover Rate' },
            ]}
          />
        </ChartCard>

        {/* Top Products */}
        <Card>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">Top Products</h3>
          <div className="space-y-3">
            {topProducts.map((product, i) => (
              <motion.div
                key={product.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-center gap-3 p-2 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800 transition-all"
              >
                <span className="w-6 h-6 rounded-lg bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{product.name}</p>
                  <p className="text-xs text-slate-500">{formatCurrency(product.revenue)}</p>
                </div>
                <span className={`text-xs font-medium ${product.growth >= 0 ? 'text-success' : 'text-danger'}`}>
                  {formatPercent(product.growth)}
                </span>
              </motion.div>
            ))}
          </div>
        </Card>

        {/* Critical Alerts */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Critical Alerts</h3>
            <AlertTriangle size={16} className="text-warning" />
          </div>
          <div className="space-y-3">
            {criticalAlerts.map((alert) => (
              <div key={alert.id} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700">
                <div className="flex items-start gap-2">
                  <StatusChip status={alert.type} />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-slate-900 dark:text-white">{alert.title}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{alert.description}</p>
                    <p className="text-[10px] text-slate-400 mt-1">{alert.time}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Recommendations + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={16} className="text-primary" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Recent AI Recommendations</h3>
          </div>
          <div className="space-y-3">
            {recentRecommendations.map((rec) => (
              <div key={rec.id} className="flex items-center gap-3 p-3 rounded-xl border border-slate-100 dark:border-slate-700 hover:border-primary/20 transition-all cursor-pointer" onClick={() => navigate('/copilot')}>
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-900 dark:text-white">{rec.title}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{rec.impact} · {rec.confidence}% confidence</p>
                </div>
                <StatusChip status={rec.priority} />
                <ArrowRight size={14} className="text-slate-400" />
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">Quick Actions</h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Run AI Analysis', desc: 'Investigate business issues', path: '/copilot', color: 'from-violet-500 to-primary' },
              { label: 'View Reports', desc: 'Executive summaries', path: '/reports', color: 'from-blue-500 to-cyan-500' },
              { label: 'Check Inventory', desc: 'Stock health overview', path: '/inventory', color: 'from-emerald-500 to-teal-500' },
              { label: 'Campaign Review', desc: 'Marketing performance', path: '/campaigns', color: 'from-orange-500 to-amber-500' },
            ].map((action) => (
              <button
                key={action.label}
                onClick={() => navigate(action.path)}
                className="p-4 rounded-xl text-left border border-slate-200 dark:border-slate-700 hover:shadow-md transition-all duration-200 group"
              >
                <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${action.color} mb-2 group-hover:scale-110 transition-transform`} />
                <p className="text-sm font-medium text-slate-900 dark:text-white">{action.label}</p>
                <p className="text-xs text-slate-500 mt-0.5">{action.desc}</p>
              </button>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
