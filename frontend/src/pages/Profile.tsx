import { useEffect, useState } from 'react'
import { Leaf, Mail, MapPin, Receipt, Save, User } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'

type Order = {
  id: string; restaurant: string; city_id: string; kind: string; meal: string; party_size: number; slot: string
  coupon: string | null; subtotal: number; discount: number; total: number; status: string; created_at: string
  items: { name: string; qty: number }[]
}

export default function Profile() {
  const { user, setUser } = useAuth()
  const [form, setForm] = useState({ full_name: '', email: '', home_city: '', diet: 'vegetarian' })
  const [orders, setOrders] = useState<Order[]>([])
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (user) setForm({ full_name: user.full_name, email: user.email, home_city: user.home_city, diet: user.diet })
  }, [user])
  useEffect(() => {
    api<Order[]>('/orders').then(setOrders)
  }, [])

  const save = async () => {
    setUser(await api('/me', { method: 'PUT', body: form }))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const savedTotal = orders.reduce((s, o) => s + o.discount, 0)

  return (
    <div className="grid">
      <div className="page-grid">
        <div className="card section">
          <h3><User size={17} /> Traveller profile</h3>
          <div className="row" style={{ marginBottom: 18, gap: 14 }}>
            <div className="avatar" style={{ width: 58, height: 58, fontSize: 20 }}>
              {(form.full_name || '?').split(' ').map((s) => s[0]).join('').slice(0, 2)}
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: 18 }}>{form.full_name}</div>
              <div className="faint">@{user?.username}</div>
            </div>
          </div>
          <div className="grid">
            <label className="field">Full name<input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>
            <label className="field"><span className="row" style={{ gap: 6 }}><Mail size={13} /> Email</span><input className="input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
            <label className="field"><span className="row" style={{ gap: 6 }}><MapPin size={13} /> Home city</span><input className="input" value={form.home_city} onChange={(e) => setForm({ ...form, home_city: e.target.value })} /></label>
            <label className="field"><span className="row" style={{ gap: 6 }}><Leaf size={13} /> Default diet</span>
              <select className="input" value={form.diet} onChange={(e) => setForm({ ...form, diet: e.target.value })}>
                <option value="vegetarian">Vegetarian</option><option value="vegan">Vegan</option><option value="any">Non-veg / any</option>
              </select>
            </label>
            <button className="btn primary" onClick={save}><Save size={15} /> {saved ? 'Saved ✓' : 'Save profile'}</button>
          </div>
        </div>
        <div className="grid" style={{ alignContent: 'start' }}>
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <div className="card stat-tile"><div className="v">{orders.filter((o) => o.kind === 'order_online').length}</div><div className="l">online orders</div></div>
            <div className="card stat-tile"><div className="v">{orders.filter((o) => o.kind === 'dine_in').length}</div><div className="l">table bookings</div></div>
            <div className="card stat-tile"><div className="v" style={{ color: 'var(--green)' }}>{savedTotal.toFixed(2)}</div><div className="l">saved with coupons</div></div>
            <div className="card stat-tile"><div className="v">{new Set(orders.map((o) => o.city_id)).size}</div><div className="l">cities eaten in</div></div>
          </div>
        </div>
      </div>
      <div className="card section">
        <h3><Receipt size={17} /> Orders & bookings</h3>
        {orders.length ? (
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead><tr><th>Ref</th><th>Restaurant</th><th>Type</th><th>Meal</th><th>When</th><th>Coupon</th><th style={{ textAlign: 'right' }}>Total</th><th>Status</th></tr></thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.id}>
                    <td className="mono">{o.id}</td>
                    <td>{o.restaurant}<div className="faint" style={{ fontSize: 11.5, textTransform: 'capitalize' }}>{o.city_id}</div></td>
                    <td><span className={`chip ${o.kind === 'dine_in' ? 'blue' : 'green'}`}>{o.kind === 'dine_in' ? 'dine in' : 'online'}</span></td>
                    <td style={{ textTransform: 'capitalize' }}>{o.meal}</td>
                    <td>{o.slot} · {o.party_size}p</td>
                    <td>{o.coupon ? <code style={{ color: 'var(--amber)' }}>{o.coupon}</code> : '—'}</td>
                    <td className="mono" style={{ textAlign: 'right' }}>{o.total.toFixed(2)}</td>
                    <td className="muted">{o.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p className="muted">No orders yet — find a restaurant on the dashboard and order or book a table.</p>}
      </div>
    </div>
  )
}
