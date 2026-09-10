import { useEffect, useState } from 'react'
import Button from '../ui/Button'
import Modal from '../ui/Modal'

const FIELDS = [
  { key: 'sku', label: 'SKU', type: 'text', required: true },
  { key: 'name', label: 'Name', type: 'text', required: true },
  { key: 'supplier', label: 'Supplier', type: 'text' },
  { key: 'price', label: 'Price', type: 'number', step: '0.01', required: true },
  { key: 'cost', label: 'Cost', type: 'number', step: '0.01', required: true },
]

const EMPTY = { sku: '', name: '', supplier: '', price: '', cost: '', category_id: '', status: 'active' }

export default function ProductForm({ open, onClose, onSubmit, categories, product }) {
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const editing = !!product

  useEffect(() => {
    if (open) {
      setError('')
      setForm(product
        ? {
            sku: product.id, name: product.name, supplier: product.supplier ?? '',
            price: product.price, cost: product.cost,
            category_id: categories.find((c) => c.name === product.category)?.id ?? '',
            status: product.status,
          }
        : { ...EMPTY, category_id: categories[0]?.id ?? '' })
    }
  }, [open, product, categories])

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await onSubmit({
        ...(editing ? {} : { sku: form.sku }),
        name: form.name,
        supplier: form.supplier || null,
        price: Number(form.price),
        cost: Number(form.cost),
        category_id: Number(form.category_id),
        status: form.status,
      })
      onClose()
    } catch (err) {
      setError(err.message || 'Could not save the product')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open} onClose={onClose}
      title={editing ? `Edit ${product?.name}` : 'Add product'}
      footer={
        <>
          <Button variant="secondary" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" onClick={submit} disabled={busy}>
            {busy ? 'Saving…' : editing ? 'Save changes' : 'Create product'}
          </Button>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-3">
        {FIELDS.map((f) => (
          <div key={f.key} className={editing && f.key === 'sku' ? 'opacity-50' : ''}>
            <label htmlFor={`pf-${f.key}`} className="block text-xs font-medium text-slate-500 mb-1">
              {f.label}{f.required ? ' *' : ''}
            </label>
            <input
              id={`pf-${f.key}`} type={f.type} step={f.step} required={f.required}
              disabled={editing && f.key === 'sku'}
              value={form[f.key]}
              onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed"
            />
          </div>
        ))}

        <div>
          <label htmlFor="pf-category" className="block text-xs font-medium text-slate-500 mb-1">Category *</label>
          <select
            id="pf-category" required value={form.category_id}
            onChange={(e) => setForm({ ...form, category_id: e.target.value })}
            className="w-full px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="">Select…</option>
            {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>

        {form.price && form.cost && Number(form.price) > 0 ? (
          <p className="text-xs text-slate-400">
            Margin: {(((Number(form.price) - Number(form.cost)) / Number(form.price)) * 100).toFixed(1)}%
          </p>
        ) : null}

        {error && <p role="alert" className="text-xs text-danger">{error}</p>}
      </form>
    </Modal>
  )
}
