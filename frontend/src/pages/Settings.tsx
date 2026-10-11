import { useEffect, useState } from 'react'
import { Cpu, Database, Palette, SlidersHorizontal } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'

type Health = { restaurants: number; llm: { online: boolean; model: string; models: string[] } }

function Toggle({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return <button className={`toggle ${on ? 'on' : ''}`} onClick={() => onChange(!on)} aria-pressed={on} />
}

export default function Settings() {
  const { user, setUser } = useAuth()
  const [s, setS] = useState<Record<string, any>>({})
  const [health, setHealth] = useState<Health | null>(null)
  const [toast, setToast] = useState('')

  useEffect(() => { if (user) setS(user.settings) }, [user])
  useEffect(() => { api<Health>('/health').then(setHealth) }, [])

  const update = async (patch: Record<string, any>) => {
    const next = { ...s, ...patch }
    setS(next)
    setUser(await api('/me', { method: 'PUT', body: { settings: next } }))
    setToast('Settings saved')
    setTimeout(() => setToast(''), 1600)
  }

  return (
    <div className="page-grid">
      <div className="card section">
        <h3><Palette size={17} /> Experience</h3>
        <div className="setting-row">
          <div style={{ flex: 1 }}><b>Sparkle cursor</b><div className="muted" style={{ fontSize: 13 }}>Particles follow your mouse and burst on click</div></div>
          <Toggle on={s.sparkles ?? true} onChange={(v) => update({ sparkles: v })} />
        </div>
        <div className="setting-row">
          <div style={{ flex: 1 }}><b>Show original language</b><div className="muted" style={{ fontSize: 13 }}>Keep the untranslated dish name under each translation</div></div>
          <Toggle on={s.show_original ?? true} onChange={(v) => update({ show_original: v })} />
        </div>
        <div className="setting-row">
          <div style={{ flex: 1 }}><b>Distance units</b></div>
          <select className="select" value={s.units || 'km'} onChange={(e) => update({ units: e.target.value })}>
            <option value="km">Kilometres</option><option value="mi">Miles</option>
          </select>
        </div>
      </div>

      <div className="card section">
        <h3><SlidersHorizontal size={17} /> Recommendation preferences</h3>
        <div className="setting-row">
          <div style={{ flex: 1 }}><b>Preferred currency</b><div className="muted" style={{ fontSize: 13 }}>Menus show local prices; this is used for summaries</div></div>
          <select className="select" value={s.currency || 'EUR'} onChange={(e) => update({ currency: e.target.value })}>
            {['EUR', 'GBP', 'USD', 'INR', 'CHF'].map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div className="setting-row">
          <div style={{ flex: 1 }}><b>Auto-apply best coupon</b><div className="muted" style={{ fontSize: 13 }}>The agent picks the biggest valid discount at checkout</div></div>
          <Toggle on={s.auto_coupon ?? true} onChange={(v) => update({ auto_coupon: v })} />
        </div>
        <div className="setting-row">
          <div style={{ flex: 1 }}><b>Allow automatic ordering</b><div className="muted" style={{ fontSize: 13 }}>Let the agent choose dishes and confirm orders / bookings (simulated)</div></div>
          <Toggle on={s.auto_order ?? true} onChange={(v) => update({ auto_order: v })} />
        </div>
      </div>

      <div className="card section">
        <h3><Cpu size={17} /> AI engine</h3>
        <div className="setting-row">
          <div style={{ flex: 1 }}><b>Ollama</b><div className="muted" style={{ fontSize: 13 }}>Local LLM used for intent parsing, translation and suggestions</div></div>
          <span className={`chip ${health?.llm.online ? 'green' : 'red'}`}>{health ? (health.llm.online ? 'online' : 'offline') : '…'}</span>
        </div>
        <div className="setting-row">
          <div style={{ flex: 1 }}><b>Active model</b><div className="muted" style={{ fontSize: 13 }}>Change with the EUROEAT_MODEL env var on the backend</div></div>
          <code>{health?.llm.model}</code>
        </div>
        <div className="setting-row">
          <div style={{ flex: 1 }}><b>Installed models</b></div>
          <div className="row wrap" style={{ gap: 6, justifyContent: 'flex-end' }}>{health?.llm.models.map((m) => <span key={m} className="chip">{m}</span>)}</div>
        </div>
      </div>

      <div className="card section">
        <h3><Database size={17} /> Data</h3>
        <div className="setting-row"><div style={{ flex: 1 }}><b>Restaurants in database</b></div><span className="mono">{health?.restaurants.toLocaleString()}</span></div>
        <div className="setting-row"><div style={{ flex: 1 }}><b>Refresh a city</b><div className="muted" style={{ fontSize: 13 }}>Run on the backend:</div></div></div>
        <code style={{ fontSize: 12, color: 'var(--muted)' }}>python -m app.ingest.osm barcelona</code>
      </div>
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
