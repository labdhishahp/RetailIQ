import { useEffect, useMemo, useState } from 'react'
import { Search, Filter, ChevronLeft, ChevronRight, Download, Plus, Pencil, Trash2 } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import StatusChip from '../components/ui/StatusChip'
import Button from '../components/ui/Button'
import { useDemo } from '../context/DemoContext'
import { formatCurrency } from '../data/mockData'
import { SkeletonTable } from '../components/ui/Skeleton'
import ProductForm from '../components/products/ProductForm'
import { useAuth } from '../context/AuthContext'
import {
  createProduct, deleteProduct, getCategoriesList, updateProduct,
} from '../api/retail'

const PAGE_SIZE = 8

export default function Products() {
  const { products, dataLoading, refreshData, pushToast } = useDemo()
  const { canWrite } = useAuth()
  const [categories, setCategories] = useState([])
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)

  useEffect(() => {
    getCategoriesList().then(setCategories).catch(() => setCategories([]))
  }, [])

  const handleSubmit = async (payload) => {
    if (editing) {
      const raw = await import('../api/client').then((m) => m.apiGet('/products?limit=200'))
      const match = raw.find((r) => r.sku === editing.id)
      if (!match) throw new Error('Product no longer exists')
      await updateProduct(match.id, payload)
      pushToast({ title: 'Product updated', message: payload.name, type: 'success' })
    } else {
      await createProduct(payload)
      pushToast({ title: 'Product created', message: payload.name, type: 'success' })
    }
    await refreshData({ silent: true })
  }

  const handleDelete = async (product) => {
    try {
      const raw = await import('../api/client').then((m) => m.apiGet('/products?limit=200'))
      const match = raw.find((r) => r.sku === product.id)
      if (!match) return
      await deleteProduct(match.id)
      pushToast({ title: 'Product deleted', message: product.name, type: 'info' })
      await refreshData({ silent: true })
    } catch (err) {
      pushToast({ title: 'Could not delete', message: err.message, type: 'error' })
    }
  }
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(1)

  const categoryOptions = [...new Set(products.map((p) => p.category))]

  const filtered = useMemo(() => {
    return products.filter((p) => {
      const matchSearch = p.name.toLowerCase().includes(search.toLowerCase()) || p.id.toLowerCase().includes(search.toLowerCase())
      const matchCategory = categoryFilter === 'all' || p.category === categoryFilter
      const matchStatus = statusFilter === 'all' || p.status === statusFilter
      return matchSearch && matchCategory && matchStatus
    })
  }, [products, search, categoryFilter, statusFilter])

  const exportCsv = () => {
    const header = ['SKU', 'Name', 'Category', 'Supplier', 'Price', 'Cost', 'Stock', 'Margin %', 'Status']
    const rows = filtered.map((p) => [
      p.id, p.name, p.category, p.supplier ?? '', p.price, p.cost, p.stock, p.margin, p.status,
    ])
    const csv = [header, ...rows]
      .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))
      .join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'retailiq-products.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div>
      <PageHeader
        title="Products"
        subtitle={`${filtered.length} products in catalog`}
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" icon={Download} size="sm" onClick={exportCsv}>Export</Button>
            {canWrite && (
              <Button icon={Plus} size="sm" onClick={() => { setEditing(null); setFormOpen(true) }}>
                Add product
              </Button>
            )}
          </div>
        }
      />

      {/* Filters */}
      <Card className="!p-4 mb-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search products..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              className="w-full pl-10 pr-4 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div className="flex gap-2">
            <select
              value={categoryFilter}
              onChange={(e) => { setCategoryFilter(e.target.value); setPage(1) }}
              className="px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">All Categories</option>
              {categoryOptions.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
              className="px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="low_stock">Low Stock</option>
              <option value="out_of_stock">Out of Stock</option>
              <option value="overstock">Overstock</option>
            </select>
            <Button variant="secondary" icon={Filter} size="sm">Filters</Button>
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card className="!p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50">
                {['Product ID', 'Name', 'Category', 'Supplier', 'Price', 'Stock', 'Margin', 'Status', ...(canWrite ? [''] : [])].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dataLoading && paginated.length === 0 && (
                <tr><td colSpan={canWrite ? 9 : 8} className="p-4"><SkeletonTable rows={6} cols={8} /></td></tr>
              )}
              {paginated.map((product) => (
                <tr key={product.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{product.id}</td>
                  <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">{product.name}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{product.category}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{product.supplier}</td>
                  <td className="px-4 py-3 font-medium">{formatCurrency(product.price)}</td>
                  <td className="px-4 py-3">
                    <span className={product.stock < 100 ? 'text-warning font-medium' : ''}>{product.stock}</span>
                  </td>
                  <td className="px-4 py-3 text-success font-medium">{product.margin}%</td>
                  <td className="px-4 py-3"><StatusChip status={product.status} /></td>
                  {canWrite && (
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => { setEditing(product); setFormOpen(true) }}
                          aria-label={`Edit ${product.name}`}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-primary hover:bg-primary/10 transition-colors"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => handleDelete(product)}
                          aria-label={`Delete ${product.name}`}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-danger hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 dark:border-slate-700">
          <p className="text-xs text-slate-500">
            Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30 transition-all"
            >
              <ChevronLeft size={16} />
            </button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button
                key={i}
                onClick={() => setPage(i + 1)}
                className={`w-8 h-8 rounded-lg text-xs font-medium transition-all ${page === i + 1 ? 'bg-primary text-white' : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600'}`}
              >
                {i + 1}
              </button>
            ))}
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30 transition-all"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </Card>

      <ProductForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSubmit={handleSubmit}
        categories={categories}
        product={editing}
      />
    </div>
  )
}
