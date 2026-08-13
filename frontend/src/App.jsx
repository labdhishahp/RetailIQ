import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './components/layout/MainLayout'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import Inventory from './pages/Inventory'
import Customers from './pages/Customers'
import SalesAnalytics from './pages/SalesAnalytics'
import CampaignAnalytics from './pages/CampaignAnalytics'
import AICopilot from './pages/AICopilot'
import Reports from './pages/Reports'
import DecisionHistory from './pages/DecisionHistory'
import Settings from './pages/Settings'
import Profile from './pages/Profile'

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="products" element={<Products />} />
        <Route path="inventory" element={<Inventory />} />
        <Route path="customers" element={<Customers />} />
        <Route path="analytics" element={<SalesAnalytics />} />
        <Route path="campaigns" element={<CampaignAnalytics />} />
        <Route path="copilot" element={<AICopilot />} />
        <Route path="reports" element={<Reports />} />
        <Route path="history" element={<DecisionHistory />} />
        <Route path="settings" element={<Settings />} />
        <Route path="profile" element={<Profile />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
