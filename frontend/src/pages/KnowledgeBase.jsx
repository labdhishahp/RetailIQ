import { useCallback, useEffect, useState } from 'react'
import { BookOpen, Search, Plus, Trash2, FileText, Database } from 'lucide-react'
import { motion } from 'framer-motion'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import StatusChip from '../components/ui/StatusChip'
import { SkeletonCard } from '../components/ui/Skeleton'
import {
  createDocument, deleteDocument, getDocuments, getKnowledgeStats, searchKnowledge,
} from '../api/retail'
import { useAuth } from '../context/AuthContext'
import { useDemo } from '../context/DemoContext'

const DOC_TYPES = ['policy', 'contract', 'playbook', 'competitor', 'product', 'note']

export default function KnowledgeBase() {
  const { canWrite } = useAuth()
  const { pushToast } = useDemo()
  const [documents, setDocuments] = useState([])
  const [stats, setStats] = useState({ documents: 0, chunks: 0 })
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState(null)
  const [searching, setSearching] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [draft, setDraft] = useState({ title: '', doc_type: 'note', source: '', content: '' })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [docs, s] = await Promise.all([getDocuments(), getKnowledgeStats()])
      setDocuments(docs)
      setStats(s)
    } catch (err) {
      pushToast({ title: 'Could not load knowledge base', message: err.message, type: 'error' })
    } finally {
      setLoading(false)
    }
  }, [pushToast])

  useEffect(() => { load() }, [load])

  const runSearch = async (e) => {
    e.preventDefault()
    if (query.trim().length < 2) return
    setSearching(true)
    try {
      setHits(await searchKnowledge(query))
    } catch (err) {
      pushToast({ title: 'Search failed', message: err.message, type: 'error' })
    } finally {
      setSearching(false)
    }
  }

  const submit = async (e) => {
    e.preventDefault()
    try {
      await createDocument(draft)
      pushToast({ title: 'Document indexed', message: draft.title, type: 'success' })
      setDraft({ title: '', doc_type: 'note', source: '', content: '' })
      setShowForm(false)
      load()
    } catch (err) {
      pushToast({ title: 'Could not index document', message: err.message, type: 'error' })
    }
  }

  const remove = async (id, title) => {
    try {
      await deleteDocument(id)
      pushToast({ title: 'Document removed', message: title, type: 'info' })
      load()
    } catch (err) {
      pushToast({ title: 'Delete failed', message: err.message, type: 'error' })
    }
  }

  return (
    <div>
      <PageHeader
        title="Knowledge Base"
        subtitle={`${stats.documents} documents · ${stats.chunks} embedded chunks retrievable by the copilot`}
        actions={canWrite && (
          <Button icon={Plus} size="sm" onClick={() => setShowForm((v) => !v)}>
            {showForm ? 'Cancel' : 'Add document'}
          </Button>
        )}
      />

      {showForm && canWrite && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <Card>
            <form onSubmit={submit} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label htmlFor="doc-title" className="block text-xs font-medium text-slate-500 mb-1">Title</label>
                  <input
                    id="doc-title" required value={draft.title}
                    onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                    className="w-full px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>
                <div>
                  <label htmlFor="doc-type" className="block text-xs font-medium text-slate-500 mb-1">Type</label>
                  <select
                    id="doc-type" value={draft.doc_type}
                    onChange={(e) => setDraft({ ...draft, doc_type: e.target.value })}
                    className="w-full px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    {DOC_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label htmlFor="doc-content" className="block text-xs font-medium text-slate-500 mb-1">
                  Content (chunked and embedded on save)
                </label>
                <textarea
                  id="doc-content" required rows={6} minLength={20} value={draft.content}
                  onChange={(e) => setDraft({ ...draft, content: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20 resize-y"
                />
              </div>
              <div className="flex justify-end">
                <Button type="submit" size="sm">Index document</Button>
              </div>
            </form>
          </Card>
        </motion.div>
      )}

      <Card className="!p-4 mb-6">
        <form onSubmit={runSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="search" value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="Search the knowledge base (hybrid vector + full-text)…"
              aria-label="Search knowledge base"
              className="w-full pl-10 pr-4 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <Button type="submit" size="sm" disabled={searching}>{searching ? 'Searching…' : 'Search'}</Button>
        </form>

        {hits && (
          <div className="mt-4 space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              {hits.length} result(s)
            </p>
            {hits.map((h) => (
              <div key={h.chunk_id} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60">
                <div className="flex items-center gap-2 mb-1">
                  <FileText size={13} className="text-primary" />
                  <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">{h.title}</span>
                  <StatusChip status={h.doc_type} label={h.doc_type} />
                  <span className="ml-auto text-[10px] text-slate-400">
                    score {h.score.toFixed(4)}{h.similarity != null ? ` · sim ${(h.similarity * 100).toFixed(0)}%` : ''}
                  </span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">{h.content.slice(0, 300)}…</p>
              </div>
            ))}
          </div>
        )}
      </Card>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => <SkeletonCard key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {documents.map((d) => (
            <Card key={d.id} hover className="h-full flex flex-col">
              <div className="flex items-start justify-between mb-2">
                <div className="p-2 rounded-xl bg-violet-100 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400">
                  <BookOpen size={16} />
                </div>
                <StatusChip status={d.doc_type} label={d.doc_type} />
              </div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{d.title}</h3>
              {d.source && <p className="text-xs text-slate-400 mt-0.5">{d.source}</p>}
              <div className="mt-auto pt-3 flex items-center justify-between">
                <span className="inline-flex items-center gap-1 text-[10px] text-slate-400">
                  <Database size={11} /> indexed
                </span>
                {canWrite && (
                  <button
                    onClick={() => remove(d.id, d.title)}
                    aria-label={`Delete ${d.title}`}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-danger hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
