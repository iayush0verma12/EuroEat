import { useEffect, useMemo, useState } from 'react'
import { Bike, Bot, CalendarCheck, Check, Minus, Plus, Ticket, Utensils, X } from 'lucide-react'
import { api, type Recommendation } from '../api'

type Coupon = { code: string; title: string; applicable: boolean; reason: string | null; discount: number }
type Kind = 'order_online' | 'dine_in'

const SLOTS: Record<string, string[]> = {
  breakfast: ['08:30', '09:00', '09:30', '10:00', '10:30'],
  lunch: ['12:30', '13:00', '13:30', '14:00', '14:30'],
  dinner: ['19:30', '20:00', '20:30', '21:00', '21:30'],
}

export default function OrderModal({
  rest, meal, initialKind, diet, onClose,
}: { rest: Recommendation; meal: string; initialKind: Kind; diet: string; onClose: () => void }) {
  const [kind, setKind] = useState<Kind>(initialKind)
  const [qty, setQty] = useState<Record<number, number>>({})
  const [party, setParty] = useState(2)
  const [slot, setSlot] = useState(SLOTS[meal]?.[2] || '20:00')
  const [coupons, setCoupons] = useState<{ best: Coupon | null; all: Coupon[]; partner: boolean } | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<any>(null)
  const [err, setErr] = useState('')

  const items = rest.menu.items
  const subtotal = useMemo(
    () => Math.round(items.reduce((s, it, i) => s + (qty[i] || 0) * it.price, 0) * 100) / 100,
    [qty, items],
  )

  useEffect(() => {
    const t = setTimeout(() => {
      api('/coupons/evaluate', { body: { restaurant_id: rest.id, kind, meal, subtotal } })
        .then((c) => {
          setCoupons(c)
          setSelected(c.best?.code ?? null)
        })
        .catch(() => {})
    }, 250)
    return () => clearTimeout(t)
  }, [subtotal, kind, meal, rest.id])

  const discount = coupons?.all.find((c) => c.code === selected && c.applicable)?.discount || 0
  const delivery = kind === 'order_online' ? 3.5 : 0
  const total = Math.max(subtotal - discount, 0) + delivery
  const cur = rest.currency

  const place = async () => {
    setBusy(true)
    setErr('')
    try {
      const body = {
        restaurant_id: rest.id, kind, meal, party_size: party, slot,
        coupon: selected,
        items: items.map((it, i) => ({ name: it.name_en || it.name, price: it.price, qty: qty[i] || 0 })).filter((x) => x.qty > 0),
      }
      setDone(await api('/orders', { body }))
    } catch (e: any) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  const auto = async () => {
    setBusy(true)
    setErr('')
    try {
      setDone(await api('/orders/auto', { body: { restaurant_id: rest.id, kind, meal, party_size: party, diet, slot } }))
    } catch (e: any) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="card modal" onClick={(e) => e.stopPropagation()}>
        <div className="row" style={{ marginBottom: 16 }}>
          <div>
            <div className="faint" style={{ fontSize: 12 }}>{meal.toUpperCase()}</div>
            <h2 style={{ fontSize: 20 }}>{rest.name}</h2>
          </div>
          <div className="spacer" />
          <button className="btn ghost sm" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>

        {done ? (
          <div className="success-burst">
            <div className="check"><Check size={32} /></div>
            <h3 style={{ fontSize: 20 }}>{done.kind === 'dine_in' ? 'Table booked!' : 'Order placed!'}</h3>
            <p className="muted">
              Confirmation <code style={{ color: 'var(--amber)' }}>{done.id}</code> · {done.slot} · party of {done.party_size}
              {done.eta && <> · ETA {done.eta}</>}
            </p>
            {done.agent_note && <p className="chip blue" style={{ margin: '6px auto' }}><Bot size={12} /> {done.agent_note}</p>}
            <table className="menu-table" style={{ margin: '14px 0', textAlign: 'left' }}>
              <tbody>
                {done.items.map((it: any, i: number) => (
                  <tr key={i}><td>{it.qty} × {it.name}</td><td className="price">{(it.price * it.qty).toFixed(2)} {done.currency}</td></tr>
                ))}
                {done.coupon && <tr><td>Coupon <code>{done.coupon.code}</code></td><td className="price">−{done.discount.toFixed(2)}</td></tr>}
                {done.delivery_fee > 0 && <tr><td>Delivery</td><td className="price">{done.delivery_fee.toFixed(2)}</td></tr>}
                <tr><td><b>Total</b></td><td className="price"><b>{done.total.toFixed(2)} {done.currency}</b></td></tr>
              </tbody>
            </table>
            <p className="faint" style={{ fontSize: 12 }}>
              Simulated — no real payment or reservation was made. Status: {done.status}.
              {rest.links.website && <> Book directly on the <a href={rest.links.website} target="_blank" rel="noreferrer">restaurant website</a>.</>}
            </p>
            <button className="btn primary" onClick={onClose}>Done</button>
          </div>
        ) : (
          <>
            <div className="seg" style={{ marginBottom: 18 }}>
              <button className={kind === 'order_online' ? 'on' : ''} onClick={() => setKind('order_online')}><Bike size={15} /> Order online</button>
              <button className={kind === 'dine_in' ? 'on' : ''} onClick={() => setKind('dine_in')}><Utensils size={15} /> Dine in</button>
            </div>

            <div className="row wrap" style={{ marginBottom: 16, gap: 14 }}>
              <label className="field" style={{ flex: 1, minWidth: 120 }}>
                {kind === 'dine_in' ? 'Party size' : 'People'}
                <select className="input" value={party} onChange={(e) => setParty(+e.target.value)}>
                  {[1, 2, 3, 4, 5, 6, 8].map((n) => <option key={n}>{n}</option>)}
                </select>
              </label>
              <label className="field" style={{ flex: 1, minWidth: 120 }}>
                {kind === 'dine_in' ? 'Table time' : 'Deliver at'}
                <select className="input" value={slot} onChange={(e) => setSlot(e.target.value)}>
                  {(SLOTS[meal] || SLOTS.dinner).map((s) => <option key={s}>{s}</option>)}
                </select>
              </label>
            </div>

            <div className="sub-h">{kind === 'dine_in' ? 'Pre-order (optional)' : 'Choose dishes'}</div>
            <table className="menu-table" style={{ marginBottom: 16 }}>
              <tbody>
                {items.map((it, i) => (
                  <tr key={i}>
                    <td>
                      {it.name_en || it.name}
                      {it.name_en && it.name_en !== it.name && <div className="orig">{it.name}</div>}
                    </td>
                    <td className="price">{it.price.toFixed(2)}</td>
                    <td style={{ width: 96, textAlign: 'right' }}>
                      <span className="qty">
                        <button onClick={() => setQty({ ...qty, [i]: Math.max((qty[i] || 0) - 1, 0) })}><Minus size={12} /></button>
                        <span style={{ minWidth: 14, textAlign: 'center' }}>{qty[i] || 0}</span>
                        <button onClick={() => setQty({ ...qty, [i]: (qty[i] || 0) + 1 })}><Plus size={12} /></button>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="sub-h"><Ticket size={13} /> Coupons {coupons?.partner && <span className="chip amber">partner restaurant</span>}</div>
            {coupons?.all.map((c) => (
              <div key={c.code} className={`coupon ${c.code === coupons.best?.code ? 'best' : ''} ${c.applicable ? '' : 'na'}`}
                onClick={() => c.applicable && setSelected(c.code)} style={{ cursor: c.applicable ? 'pointer' : 'default' }}>
                <input type="radio" readOnly checked={selected === c.code} disabled={!c.applicable} />
                <code>{c.code}</code>
                <span style={{ flex: 1 }}>{c.title}</span>
                {c.applicable ? <b style={{ color: 'var(--green)' }}>−{c.discount.toFixed(2)}</b> : <span className="faint" style={{ fontSize: 11.5 }}>{c.reason}</span>}
                {c.code === coupons.best?.code && <span className="chip amber">best</span>}
              </div>
            ))}

            <div className="card" style={{ padding: 14, marginTop: 14, boxShadow: 'none' }}>
              <div className="row"><span className="muted">Subtotal</span><span className="spacer" /><span className="mono">{subtotal.toFixed(2)} {cur}</span></div>
              {discount > 0 && <div className="row"><span className="muted">Discount ({selected})</span><span className="spacer" /><span className="mono" style={{ color: 'var(--green)' }}>−{discount.toFixed(2)}</span></div>}
              {delivery > 0 && <div className="row"><span className="muted">Delivery</span><span className="spacer" /><span className="mono">{delivery.toFixed(2)}</span></div>}
              <div className="row" style={{ marginTop: 6, fontWeight: 800 }}><span>Total</span><span className="spacer" /><span className="mono">{total.toFixed(2)} {cur}</span></div>
            </div>

            {err && <div className="chip red" style={{ marginTop: 10 }}>{err}</div>}
            <div className="row wrap" style={{ marginTop: 16, justifyContent: 'flex-end' }}>
              <button className="btn" onClick={auto} disabled={busy} title="The agent picks dishes, applies the best coupon and confirms">
                <Bot size={16} /> Let the agent {kind === 'dine_in' ? 'book' : 'order'} automatically
              </button>
              <button className="btn primary" onClick={place} disabled={busy || (kind === 'order_online' && subtotal === 0)}>
                {kind === 'dine_in' ? <><CalendarCheck size={16} /> Book table</> : <><Bike size={16} /> Place order</>}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
