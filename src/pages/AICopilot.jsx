import { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, RotateCcw, PanelRightOpen, PanelRightClose } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import ChatMessage, { TypingIndicator } from '../components/copilot/ChatMessage'
import AgentCard from '../components/copilot/AgentCard'
import RecommendationCard from '../components/copilot/RecommendationCard'
import SimulationPanel from '../components/copilot/SimulationPanel'
import PromptSuggestions from '../components/copilot/PromptSuggestions'
import { useInvestigation } from '../hooks/useInvestigation'
import { promptSuggestions } from '../data/mockData'

export default function AICopilot() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [showSimulation, setShowSimulation] = useState(true)
  const [conversations] = useState([
    { id: 1, title: 'Shampoo sales decline', date: 'Today' },
    { id: 2, title: 'Inventory reorder analysis', date: 'Yesterday' },
    { id: 3, title: 'Summer campaign ROI', date: 'Jul 14' },
    { id: 4, title: 'Customer churn risk', date: 'Jul 12' },
  ])
  const chatEndRef = useRef(null)
  const {
    phase, activeAgentIndex, completedAgents, agentProgress,
    result, agents, startInvestigation, reset,
  } = useInvestigation()

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, phase, result])

  const handleSend = (text) => {
    const query = text || input.trim()
    if (!query) return

    setInput('')
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: query, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) },
    ])

    setTimeout(() => {
      startInvestigation(query)
    }, 300)
  }

  const handleNewChat = () => {
    setMessages([])
    reset()
    setInput('')
  }

  const getAgentStatus = (index) => {
    const agent = agents[index]
    if (completedAgents.includes(agent.id)) return 'complete'
    if (index === activeAgentIndex) return 'active'
    if (index < activeAgentIndex || completedAgents.length > index) return 'complete'
    return 'pending'
  }

  return (
    <div>
      <PageHeader
        title="AI Business Copilot"
        subtitle="Ask questions in natural language — RetailIQ investigates automatically"
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" icon={RotateCcw} size="sm" onClick={handleNewChat}>New Chat</Button>
            <Button
              variant="secondary"
              icon={showSimulation ? PanelRightClose : PanelRightOpen}
              size="sm"
              onClick={() => setShowSimulation(!showSimulation)}
            >
              {showSimulation ? 'Hide' : 'Show'} Simulation
            </Button>
          </div>
        }
      />

      <div className={`grid gap-4 ${showSimulation ? 'grid-cols-1 xl:grid-cols-3' : 'grid-cols-1'}`}>
        {/* Main Chat Area */}
        <div className={showSimulation ? 'xl:col-span-2' : ''}>
          <Card className="!p-0 flex flex-col" style={{ height: 'calc(100vh - 220px)', minHeight: 500 }}>
            {/* Conversation History Sidebar (inline) */}
            {messages.length === 0 && phase === 'idle' && (
              <div className="flex-1 flex flex-col items-center justify-center p-8">
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-primary flex items-center justify-center mb-4 shadow-lg shadow-primary/25"
                >
                  <Sparkles size={28} className="text-white" />
                </motion.div>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">How can I help you today?</h2>
                <p className="text-sm text-slate-500 mb-6 text-center max-w-md">
                  Ask any business question. I'll deploy specialized AI agents to investigate sales, inventory, pricing, campaigns, and customers.
                </p>
                <PromptSuggestions suggestions={promptSuggestions} onSelect={handleSend} />
              </div>
            )}

            {/* Chat Messages */}
            {(messages.length > 0 || phase !== 'idle') && (
              <div className="flex-1 overflow-y-auto p-5 space-y-4 scrollbar-thin">
                {messages.map((msg, i) => (
                  <ChatMessage key={i} role={msg.role} content={msg.content} timestamp={msg.timestamp} />
                ))}

                {/* Investigation Flow */}
                {phase === 'investigating' && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="space-y-3 mt-4"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-primary flex items-center justify-center">
                        <Sparkles size={16} className="text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-slate-900 dark:text-white">Investigation in Progress</p>
                        <p className="text-xs text-slate-500">Deploying specialized AI agents...</p>
                      </div>
                    </div>
                    {agents.map((agent, i) => (
                      <AgentCard
                        key={agent.id}
                        agent={agent}
                        status={getAgentStatus(i)}
                        progress={agentProgress[agent.id] || 0}
                        index={i}
                      />
                    ))}
                  </motion.div>
                )}

                {/* Final Result */}
                {phase === 'complete' && result && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <ChatMessage
                      role="assistant"
                      content="Investigation complete. Here's my analysis and recommendation:"
                      timestamp={new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    />
                    <div className="ml-11 mt-3">
                      <RecommendationCard result={result} />
                    </div>
                  </motion.div>
                )}

                <div ref={chatEndRef} />
              </div>
            )}

            {/* Input Area */}
            <div className="p-4 border-t border-slate-200 dark:border-slate-700">
              <div className="flex items-end gap-2">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
                  placeholder="Ask a business question..."
                  rows={1}
                  disabled={phase === 'investigating'}
                  className="flex-1 px-4 py-3 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none disabled:opacity-50"
                />
                <Button
                  onClick={() => handleSend()}
                  disabled={!input.trim() || phase === 'investigating'}
                  icon={Send}
                  className="!rounded-xl !px-4"
                >
                  Send
                </Button>
              </div>
              <p className="text-[10px] text-slate-400 mt-2 text-center">
                RetailIQ AI may produce inaccurate information. Verify important decisions with your data team.
              </p>
            </div>
          </Card>

          {/* Past Conversations */}
          {messages.length === 0 && phase === 'idle' && (
            <div className="mt-4">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Recent Conversations</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {conversations.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => handleSend(conv.title === 'Shampoo sales decline' ? 'Why are shampoo sales decreasing?' : conv.title)}
                    className="p-3 rounded-xl text-left text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 hover:border-primary/30 transition-all"
                  >
                    <p className="font-medium text-slate-900 dark:text-white truncate">{conv.title}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">{conv.date}</p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Simulation Panel */}
        <AnimatePresence>
          {showSimulation && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <SimulationPanel />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
