import { useState } from 'react'
import { Bike, BookOpen, ExternalLink, FileText, Globe, Leaf, MapPin, Map as MapIcon, ThumbsDown, ThumbsUp, Target, Utensils } from 'lucide-react'
import type { Recommendation, Review } from '../api'
import OrderModal from './OrderModal'

const LANG: Record<string, string> = { es: 'Spanish', fr: 'French', it: 'Italian', de: 'German', pt: 'Portuguese', nl: 'Dutch', en: 'English' }

function Stars({ n }: { n: number }) {
  return <span className="stars">{'★'.repeat(Math.round(n))}{'☆'.repeat(5 - Math.round(n))}</span>
}

function ReviewBox({ r, kind }: { r: Review; kind: 'pos' | 'neg' | 'ctx' }) {
  const translated = r.lang !== 'en'
  return (
    <div className={`review ${kind}`}>
      {r.text_en}
      <div className="meta">
        <Stars n={r.rating} /> <span>{r.author}</span>
        {translated && <span className="chip blue" style={{ padding: '0 6px' }}>translated from {LANG[r.lang] || r.lang}</span>}
        {r.query && <span className="chip" style={{ padding: '0 6px' }}>matches “{r.query.split(' ').slice(0, 2).join(' ')}”{r.similarity ? ` · ${r.similarity}` : ''}</span>}
      </div>
      {translated && <details><summary>original</summary>{r.text}</details>}
    </div>
  )
}

export default function RestaurantCard({ r, rank, meal, diet }: { r: Recommendation; rank: number; meal: string; diet: string }) {
  const [order, setOrder] = useState<null | 'order_online' | 'dine_in'>(null)
  const ctx = r.context_matches.filter((c) => !r.positive.some((p) => p.text === c.text)).slice(0, 2)
  return (
    <div className="card rest-card fade-in" style={{ animationDelay: `${rank * 60}ms` }}>
      <div className="rest-head">
        <div className="rank">#{rank + 1}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="row wrap" style={{ gap: 8 }}>
            <span className="rest-name">{r.name}</span>
            {r.rating != null && <span className="chip amber">★ {r.rating} · {r.review_count} reviews</span>}
            {(r.veg_tag === 'only' || r.vegan_tag === 'only') && <span className="chip green"><Leaf size={11} /> 100% {r.vegan_tag === 'only' ? 'vegan' : 'vegetarian'}</span>}
            {r.veg_tag === 'yes' && r.vegan_tag !== 'only' && <span className="chip green"><Leaf size={11} /> veg options</span>}
          </div>
          <div className="row wrap muted" style={{ fontSize: 13, marginTop: 6, gap: 12 }}>
            {r.cuisine && <span style={{ textTransform: 'capitalize' }}>{r.cuisine}</span>}
            <span>{'€'.repeat(r.price_level || 2)}</span>
            {r.avg_price && <span>avg dish {r.avg_price.toFixed(2)} {r.currency}</span>}
            <span className="row" style={{ gap: 4 }}><MapPin size={13} /> {r.address || `${r.distance_km} km from centre`}</span>
          </div>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <button className="btn sm" onClick={() => setOrder('dine_in')}><Utensils size={14} /> Dine in</button>
          <button className="btn sm primary" onClick={() => setOrder('order_online')}><Bike size={14} /> Order</button>
        </div>
      </div>

      <div className="cols">
        <div>
          <div className="sub-h">
            <BookOpen size={13} /> Regular menu items & prices
            <span className={`chip ${r.menu.source === 'scraped' ? 'green' : 'amber'}`}>
              {r.menu.source === 'scraped' ? 'live from website' : 'estimated'}
            </span>
          </div>
          {r.menu.items.length ? (
            <table className="menu-table">
              <tbody>
                {r.menu.items.map((it, i) => (
                  <tr key={i}>
                    <td>
                      {it.vegetarian && <Leaf size={11} color="var(--green)" style={{ marginRight: 5 }} />}
                      {it.name_en || it.name}
                      {it.name_en && it.name_en.toLowerCase() !== it.name.toLowerCase() && <div className="orig">{it.name}</div>}
                    </td>
                    <td className="price">{it.price.toFixed(2)} {it.currency}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <div className="muted" style={{ fontSize: 13 }}>No {diet} items found on this menu.</div>}
          <div className="faint" style={{ fontSize: 11.5, marginTop: 6 }}>{r.menu.note}</div>
        </div>
        <div>
          <div className="sub-h"><ThumbsUp size={13} /> Positive</div>
          {r.positive.slice(0, 1).map((x, i) => <ReviewBox key={i} r={x} kind="pos" />)}
          <div className="sub-h" style={{ marginTop: 10 }}><ThumbsDown size={13} /> Negative</div>
          {r.negative.length ? r.negative.slice(0, 1).map((x, i) => <ReviewBox key={i} r={x} kind="neg" />)
            : <div className="faint" style={{ fontSize: 12.5, marginBottom: 8 }}>No negative reviews found.</div>}
          {ctx.length > 0 && <>
            <div className="sub-h" style={{ marginTop: 10 }}><Target size={13} /> About your needs</div>
            {ctx.map((x, i) => <ReviewBox key={i} r={x} kind="ctx" />)}
          </>}
        </div>
      </div>

      <div className="links">
        {r.links.website && <a href={r.links.website} target="_blank" rel="noreferrer"><Globe size={13} /> Website</a>}
        {r.links.menu && <a href={r.links.menu} target="_blank" rel="noreferrer"><FileText size={13} /> Menu page</a>}
        {r.menu.pdf && r.menu.pdf !== r.links.menu && <a href={r.menu.pdf} target="_blank" rel="noreferrer"><FileText size={13} /> Menu PDF</a>}
        <a href={r.links.google_maps} target="_blank" rel="noreferrer"><MapIcon size={13} /> Google Maps</a>
        <a href={r.links.osm} target="_blank" rel="noreferrer"><ExternalLink size={13} /> OpenStreetMap</a>
      </div>
      {order && <OrderModal rest={r} meal={meal} diet={diet} initialKind={order} onClose={() => setOrder(null)} />}
    </div>
  )
}
