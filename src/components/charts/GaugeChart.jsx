import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts'

export default function GaugeChart({ value, label = 'Health Score', height = 200 }) {
  const data = [{ name: label, value, fill: value >= 80 ? '#22C55E' : value >= 60 ? '#F59E0B' : '#EF4444' }]

  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={height}>
        <RadialBarChart cx="50%" cy="50%" innerRadius="70%" outerRadius="100%" barSize={12} data={data} startAngle={180} endAngle={0}>
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar background={{ fill: '#f1f5f9' }} dataKey="value" cornerRadius={6} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-8">
        <span className="text-3xl font-bold text-slate-900 dark:text-white">{value}</span>
        <span className="text-xs text-slate-500">{label}</span>
      </div>
    </div>
  )
}
