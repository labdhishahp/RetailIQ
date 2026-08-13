import { useState, useMemo } from 'react'
import { Search, Users, Crown, UserCheck, UserX } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import KpiCard from '../components/ui/KpiCard'
import Card from '../components/ui/Card'
import StatusChip from '../components/ui/StatusChip'
import { customers, formatCurrency } from '../data/mockData'

export default function Customers() {
  const [search, setSearch] = useState('')
  const [segmentFilter, setSegmentFilter] = useState('all')

  const filtered = useMemo(() => {
    return customers.filter((c) => {
      const matchSearch = c.name.toLowerCase().includes(search.toLowerCase()) || c.email.toLowerCase().includes(search.toLowerCase())
      const matchSegment = segmentFilter === 'all' || c.segment === segmentFilter
      return matchSearch && matchSegment
    })
  }, [search, segmentFilter])

  const stats = {
    total: customers.length,
    premium: customers.filter((c) => c.segment === 'Premium' || c.segment === 'VIP').length,
    active: customers.filter((c) => c.status === 'active').length,
    atRisk: customers.filter((c) => c.status === 'at_risk' || c.status === 'churned').length,
  }

  return (
    <div>
      <PageHeader title="Customers" subtitle={`${customers.length} customers across all segments`} />

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <KpiCard title="Total Customers" value={stats.total} icon={Users} format="number" delay={0} />
        <KpiCard title="Premium & VIP" value={stats.premium} icon={Crown} format="number" delay={0.05} />
        <KpiCard title="Active" value={stats.active} icon={UserCheck} format="number" delay={0.1} />
        <KpiCard title="At Risk / Churned" value={stats.atRisk} icon={UserX} format="number" delay={0.15} />
      </div>

      <Card className="!p-4 mb-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search customers..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <select
            value={segmentFilter}
            onChange={(e) => setSegmentFilter(e.target.value)}
            className="px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">All Segments</option>
            <option value="VIP">VIP</option>
            <option value="Premium">Premium</option>
            <option value="Regular">Regular</option>
          </select>
        </div>
      </Card>

      <Card className="!p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50">
                {['Customer', 'Email', 'Segment', 'Orders', 'Total Spent', 'Last Order', 'Status'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((customer) => (
                <tr key={customer.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">
                        {customer.name.split(' ').map((n) => n[0]).join('')}
                      </div>
                      <div>
                        <p className="font-medium text-slate-900 dark:text-white">{customer.name}</p>
                        <p className="text-xs text-slate-400">{customer.id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{customer.email}</td>
                  <td className="px-4 py-3"><StatusChip status={customer.segment} /></td>
                  <td className="px-4 py-3 font-medium">{customer.orders}</td>
                  <td className="px-4 py-3 font-medium">{formatCurrency(customer.spent)}</td>
                  <td className="px-4 py-3 text-slate-500">{customer.lastOrder}</td>
                  <td className="px-4 py-3"><StatusChip status={customer.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
