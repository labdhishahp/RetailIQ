import { useEffect, useState, useRef } from 'react'
import { motion, animate } from 'framer-motion'
import { formatCurrency, formatNumber } from '../../data/mockData'

function formatValue(v, format) {
  const rounded = Math.round(v)
  if (format === 'currency') return formatCurrency(rounded)
  if (format === 'number') return formatNumber(rounded)
  if (format === 'percent') return `${Math.round(v)}%`
  return String(rounded)
}

export default function AnimatedCounter({ value, format = 'currency', className = '' }) {
  const prevRef = useRef(value)
  const [display, setDisplay] = useState(formatValue(value, format))
  const [pulse, setPulse] = useState(false)

  useEffect(() => {
    const from = prevRef.current
    prevRef.current = value
    if (from === value) return

    const controls = animate(from, value, {
      duration: 0.8,
      ease: [0.25, 0.1, 0.25, 1],
      onUpdate: (v) => setDisplay(formatValue(v, format)),
    })
    setPulse(true)
    const t = setTimeout(() => setPulse(false), 400)
    return () => {
      controls.stop()
      clearTimeout(t)
    }
  }, [value, format])

  return (
    <motion.span
      animate={{ scale: pulse ? [1, 1.05, 1] : 1 }}
      transition={{ duration: 0.35 }}
      className={className}
    >
      {display}
    </motion.span>
  )
}
