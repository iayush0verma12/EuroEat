import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import SparkleCursor from './components/SparkleCursor'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import AssistedSearch from './pages/AssistedSearch'
import Stats from './pages/Stats'
import Profile from './pages/Profile'
import Settings from './pages/Settings'
import About from './pages/About'

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="map-loading">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const { user } = useAuth()
  const sparkles = user?.settings?.sparkles ?? true
  return (
    <>
      <div className="aurora"><span /></div>
      <div className="grid-bg" />
      <SparkleCursor enabled={sparkles} />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/app" element={<Protected><Layout /></Protected>}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="assisted" element={<AssistedSearch />} />
          <Route path="stats" element={<Stats />} />
          <Route path="profile" element={<Profile />} />
          <Route path="settings" element={<Settings />} />
          <Route path="about" element={<About />} />
        </Route>
        <Route path="*" element={<Navigate to={user ? '/app/dashboard' : '/login'} replace />} />
      </Routes>
    </>
  )
}
