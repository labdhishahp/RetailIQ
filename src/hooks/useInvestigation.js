import { useState, useCallback } from 'react'
import { investigationAgents, shampooInvestigationResult } from '../data/mockData'

export function useInvestigation() {
  const [phase, setPhase] = useState('idle') // idle | investigating | complete
  const [activeAgentIndex, setActiveAgentIndex] = useState(-1)
  const [completedAgents, setCompletedAgents] = useState([])
  const [agentProgress, setAgentProgress] = useState({})
  const [result, setResult] = useState(null)

  const startInvestigation = useCallback((query) => {
    const isShampooQuery = query.toLowerCase().includes('shampoo')

    setPhase('investigating')
    setActiveAgentIndex(0)
    setCompletedAgents([])
    setAgentProgress({})
    setResult(null)

    let currentIndex = 0

    const runAgent = (index) => {
      if (index >= investigationAgents.length) {
        setPhase('complete')
        setActiveAgentIndex(-1)
        if (isShampooQuery) {
          setResult(shampooInvestigationResult)
        } else {
          setResult({
            ...shampooInvestigationResult,
            rootCause: `Analysis complete for: "${query}". Multiple factors identified across sales, inventory, and customer data.`,
            suggestedCampaign: 'Targeted promotional campaign based on identified opportunities',
          })
        }
        return
      }

      setActiveAgentIndex(index)
      const agent = investigationAgents[index]
      const startTime = Date.now()
      const duration = agent.duration

      const progressInterval = setInterval(() => {
        const elapsed = Date.now() - startTime
        const progress = Math.min((elapsed / duration) * 100, 100)
        setAgentProgress((prev) => ({ ...prev, [agent.id]: progress }))
      }, 50)

      setTimeout(() => {
        clearInterval(progressInterval)
        setAgentProgress((prev) => ({ ...prev, [agent.id]: 100 }))
        setCompletedAgents((prev) => [...prev, agent.id])
        currentIndex = index + 1
        runAgent(currentIndex)
      }, duration)
    }

    runAgent(0)
  }, [])

  const reset = useCallback(() => {
    setPhase('idle')
    setActiveAgentIndex(-1)
    setCompletedAgents([])
    setAgentProgress({})
    setResult(null)
  }, [])

  return {
    phase,
    activeAgentIndex,
    completedAgents,
    agentProgress,
    result,
    agents: investigationAgents,
    startInvestigation,
    reset,
  }
}
