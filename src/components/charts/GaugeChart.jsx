import { useEffect, useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts'

export default function GaugeChart({ value, label = 'Health Score', height = 200 }) {
  const [displayValue, setDisplayValue] = useState(value)
  const prevValue = useRef(value)
  const fill = value >= 80 ? '#22C55E' : value >= 60 ? '#F59E0B' : '#EF4444'
  const data = [{ name: label, value: displayValue, fill }]

  useEffect(() => {
    const start = prevValue.current
    const diff = value - start
    const duration = 1200
    const startTime = Date.now()
    prevValue.current = value

    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplayValue(Math.round(start + diff * eased))
      if (progress < 1) requestAnimationFrame(animate)
    }

    requestAnimationFrame(animate)
  }, [value])

  return (
    <div className="relative">
      <motion.div
        key={value}
        initial={{ opacity: 0.6 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <ResponsiveContainer width="100%" height={height}>
          <RadialBarChart cx="50%" cy="50%" innerRadius="70%" outerRadius="100%" barSize={12} data={data} startAngle={180} endAngle={0}>
            <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
            <RadialBar background={{ fill: '#f1f5f9' }} dataKey="value" cornerRadius={6} isAnimationActive animationDuration={1200} />
          </RadialBarChart>
        </ResponsiveContainer>
      </motion.div>
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-8">
        <motion.span
          key={displayValue}
          initial={{ scale: 0.9, opacity: 0.5 }}
          animate={{ scale: 1, opacity: 1 }}
          className="text-3xl font-bold text-slate-900 dark:text-white"
        >
          {displayValue}
        </motion.span>
        <span className="text-xs text-slate-500">{label}</span>
      </div>
    </div>
  )
}
