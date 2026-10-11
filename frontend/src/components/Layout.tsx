import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { BarChart3, Compass, Info, LayoutDashboard, LogOut, Menu, Settings, Sparkles, User, UtensilsCrossed } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'

const TITLES: Record<string, string> = {
  dashboard: 'Dashboard',
  assisted: 'Assisted search',
  stats: 'Stats · 3D Europe',
  profile: 'Profile',
  settings: 'Settings',
  about: 'About',
}

export default function Layout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [open, setOpen] = useState(false)
  const [health, setHealth] = useState<{ restaurants: number; llm: { online: boolean; model: string } } | null>(null)

  useEffect(() => {
    api('/health').then(setHealth).catch(() => {})
  }, [])
  useEffect(() => setOpen(false), [loc.pathname])

  const key = loc.pathname.split('/')[2] || 'dashboard'
  const initials = (user?.full_name || user?.username || '?').split(' ').map((s) => s[0]).join('').slice(0, 2)

  return (
    <div className="shell">
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="brand">
          <div className="brand-logo"><UtensilsCrossed size={19} /></div>
          <div>EuroEat<small>AI restaurant agent</small></div>
        </div>
        <NavLink to="/app/dashboard" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={18} /> Dashboard
        </NavLink>
        <NavLink to="/app/assisted" className={({ isActive }) => `nav-item sub ${isActive ? 'active' : ''}`}>
          <Compass size={16} /> Assisted search
        </NavLink>
        <NavLink to="/app/stats" className={({ isActive }) => `nav-item sub ${isActive ? 'active' : ''}`}>
          <BarChart3 size={16} /> Stats
        </NavLink>
        <NavLink to="/app/profile" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <User size={18} /> Profile
        </NavLink>
        <NavLink to="/app/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Settings size={18} /> Settings
        </NavLink>
        <NavLink to="/app/about" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Info size={18} /> About
        </NavLink>

        <div className="nav-section">Agent status</div>
        <div className="row" style={{ padding: '0 12px', fontSize: 12.5 }}>
          <span className={`status-dot ${health?.llm.online ? 'on' : ''}`} />
          <span className="muted">
            {health ? (health.llm.online ? `Ollama · ${health.llm.model}` : 'LLM offline (rule fallback)') : 'checking…'}
          </span>
        </div>
        <div className="row" style={{ padding: '6px 12px', fontSize: 12.5 }}>
          <Sparkles size={13} color="var(--green)" />
          <span className="muted">{health ? `${health.restaurants.toLocaleString()} restaurants` : '…'}</span>
        </div>

        <div className="sidebar-foot">
          <div className="row">
            <div className="avatar">{initials}</div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: 13.5 }}>{user?.full_name}</div>
              <div className="faint" style={{ fontSize: 12 }}>@{user?.username}</div>
            </div>
            <div className="spacer" />
            <button className="btn ghost sm" title="Log out" onClick={() => { logout(); nav('/login') }}>
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>
      <main className="main">
        <div className="topbar">
          <button className="btn sm menu-toggle" onClick={() => setOpen(!open)} aria-label="Menu"><Menu size={16} /></button>
          <h1>{TITLES[key] || 'EuroEat'}</h1>
        </div>
        <Outlet />
      </main>
    </div>
  )
}
