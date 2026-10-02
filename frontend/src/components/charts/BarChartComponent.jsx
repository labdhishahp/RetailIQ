import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { formatCurrency } from '../../data/mockData'

const COLORS = ['#2563EB', '#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE']

export default function BarChartComponent({ data, dataKey = 'revenue', xKey = 'store', height = 280, format = 'currency' }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
        <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: 'var(--chart-axis)' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: 'var(--chart-axis)' }} axisLine={false} tickLine={false}
          tickFormatter={(v) => format === 'currency' ? `$${(v / 1000).toFixed(0)}K` : v} />
        <Tooltip
          formatter={(value) => format === 'currency' ? formatCurrency(value) : value}
          contentStyle={{ borderRadius: 8, border: '1px solid var(--tooltip-border)', backgroundColor: 'var(--tooltip-bg)', color: 'var(--text-strong)', fontSize: 12 }}
        />
        <Bar dataKey={dataKey} radius={[6, 6, 0, 0]} barSize={32}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
