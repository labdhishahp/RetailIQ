import { useCallback, useRef, useState } from 'react'
import { askCopilot } from '../api/retail'

// The agent roster shown while a request is in flight. The backend returns the
// agents it actually ran, so this list is only the optimistic view: once the
// response lands, `agents` is replaced by the real execution trace, including
// each agent's duration, the tools it called and what it found.
const PLANNED_AGENTS = [
  { id: 'sales', name: 'Sales Agent', icon: 'TrendingDown', task: 'Analysing sales trends and revenue patterns' },
  { id: 'inventory', name: 'Inventory Agent', icon: 'Package', task: 'Checking stock levels, cover and turnover' },
  { id: 'pricing', name: 'Pricing Agent', icon: 'DollarSign', task: 'Comparing realised margin against list pricing' },
  { id: 'campaign', name: 'Campaign Agent', icon: 'Megaphone', task: 'Reviewing campaign spend and return' },
  { id: 'customer', name: 'Customer Agent', icon: 'Users', task: 'Analysing segment mix and churn exposure' },
  { id: 'knowledge', name: 'Knowledge Agent', icon: 'BookOpen', task: 'Retrieving relevant policy and context documents' },
]

export function useInvestigation(onComplete) {
  const [phase, setPhase] = useState('idle')          // idle | investigating | complete | error
  const [agents, setAgents] = useState(PLANNED_AGENTS)
  const [activeAgentIndex, setActiveAgentIndex] = useState(-1)
  const [completedAgents, setCompletedAgents] = useState([])
  const [agentProgress, setAgentProgress] = useState({})
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [conversationId, setConversationId] = useState(null)
  const tickRef = useRef(null)

  const stopTicker = useCallback(() => {
    if (tickRef.current) {
      clearInterval(tickRef.current)
      tickRef.current = null
    }
  }, [])

  const startInvestigation = useCallback(async (query) => {
    setPhase('investigating')
    setAgents(PLANNED_AGENTS)
    setActiveAgentIndex(0)
    setCompletedAgents([])
    setAgentProgress({})
    setResult(null)
    setError(null)

    // The request is a single round trip, so progress is advanced on a timer
    // purely to keep the UI responsive; it is replaced by real per-agent
    // timings as soon as the response arrives.
    const started = Date.now()
    stopTicker()
    tickRef.current = setInterval(() => {
      const elapsed = Date.now() - started
      const perAgent = 2200
      const idx = Math.min(Math.floor(elapsed / perAgent), PLANNED_AGENTS.length - 1)
      setActiveAgentIndex(idx)
      setCompletedAgents(PLANNED_AGENTS.slice(0, idx).map((a) => a.id))
      setAgentProgress((prev) => {
        const next = { ...prev }
        PLANNED_AGENTS.forEach((a, i) => {
          next[a.id] = i < idx ? 100 : i === idx
            ? Math.min(((elapsed - i * perAgent) / perAgent) * 100, 95) : 0
        })
        return next
      })
    }, 80)

    try {
      const response = await askCopilot(query, conversationId)
      stopTicker()

      const realAgents = response.result.agents.map((a) => ({
        id: a.id, name: a.name, icon: a.icon, task: a.task,
        severity: a.severity, duration: a.duration,
        findings: a.findings, toolsCalled: a.toolsCalled,
      }))
      setAgents(realAgents)
      setCompletedAgents(realAgents.map((a) => a.id))
      setAgentProgress(Object.fromEntries(realAgents.map((a) => [a.id, 100])))
      setActiveAgentIndex(-1)
      setConversationId(response.conversation_id)
      setResult(response.result)
      setPhase('complete')
      onComplete?.(response.result)
      return response.result
    } catch (err) {
      stopTicker()
      setPhase('error')
      setError(err.message || 'The investigation could not be completed.')
      setActiveAgentIndex(-1)
      return null
    }
  }, [conversationId, onComplete, stopTicker])

  const reset = useCallback(() => {
    stopTicker()
    setPhase('idle')
    setAgents(PLANNED_AGENTS)
    setActiveAgentIndex(-1)
    setCompletedAgents([])
    setAgentProgress({})
    setResult(null)
    setError(null)
    setConversationId(null)
  }, [stopTicker])

  return {
    phase, activeAgentIndex, completedAgents, agentProgress,
    result, error, agents, conversationId, startInvestigation, reset,
  }
}
