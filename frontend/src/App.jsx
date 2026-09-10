import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import MainLayout from './components/layout/MainLayout'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import Inventory from './pages/Inventory'
import Customers from './pages/Customers'
import SalesAnalytics from './pages/SalesAnalytics'
import CampaignAnalytics from './pages/CampaignAnalytics'
import AICopilot from './pages/AICopilot'
import KnowledgeBase from './pages/KnowledgeBase'
import Reports from './pages/Reports'
import DecisionHistory from './pages/DecisionHistory'
import Settings from './pages/Settings'
import Profile from './pages/Profile'
import Login from './pages/Login'
import { useAuth } from './context/AuthContext'
import { DemoProvider } from './context/DemoContext'

function FullPageSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background dark:bg-slate-950">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        <p className="text-sm text-slate-400">Loading RetailIQ…</p>
      </div>
    </div>
  )
}

function RequireAuth({ children }) {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()
  if (loading) return <FullPageSpinner />
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />
  return children
}

export default function App() {
  const { isAuthenticated, loading } = useAuth()

  return (
    <Routes>
      <Route
        path="/login"
        element={
          loading ? <FullPageSpinner />
            : isAuthenticated ? <Navigate to="/" replace />
            : <Login />
        }
      />
      <Route
        element={
          <RequireAuth>
            {/* Data loading lives inside the guard so it only runs when signed in. */}
            <DemoProvider>
              <MainLayout />
            </DemoProvider>
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="products" element={<Products />} />
        <Route path="inventory" element={<Inventory />} />
        <Route path="customers" element={<Customers />} />
        <Route path="analytics" element={<SalesAnalytics />} />
        <Route path="campaigns" element={<CampaignAnalytics />} />
        <Route path="copilot" element={<AICopilot />} />
        <Route path="knowledge" element={<KnowledgeBase />} />
        <Route path="reports" element={<Reports />} />
        <Route path="history" element={<DecisionHistory />} />
        <Route path="settings" element={<Settings />} />
        <Route path="profile" element={<Profile />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
