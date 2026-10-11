import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Building2, Globe2, Leaf, Lightbulb, Minus, Plus, Search, Sparkles } from 'lucide-react'
import { api } from '../api'
import { StatsScene, type CityStat, type Hover } from '../three/StatsScene'

type Overview = {
  total: number
  veg_tagged: number
  countries: { code: string; name: string; total: number; veg_tagged: number; cities: number }[]
  cities: CityStat[]
  top_cuisines: { cuisine: string; n: number }[]
}
type Lookup = { name: string; country?: string; lat: number; lon: number; in_catalog: boolean; total: number; veg_tagged: number; id?: string | null; sample?: string[] }

export default function Stats() {
  const host = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<StatsScene | null>(null)
  const nav = useNavigate()
  const [ov, setOv] = useState<Overview | null>(null)
  const [hover, setHover] = useState<Hover>(null)
  const [country, setCountry] = useState('')
  const [cityId, setCityId] = useState('')
  const [showTotals, setShowTotals] = useState(true)
  const [vegOnly, setVegOnly] = useState(false)
  const [loading, setLoading] = useState<string | null>('Building 3D Europe…')
  const [cityInfo, setCityInfo] = useState<{ points: number; veg: number; buildings: number } | null>(null)
  const [q, setQ] = useState('')
  const [lookup, setLookup] = useState<Lookup | null>(null)
  const [lookupErr, setLookupErr] = useState('')

  useEffect(() => {
    const scene = new StatsScene(host.current!)
    sceneRef.current = scene
    scene.onHover = setHover
    scene.onPickCity = (id) => setCityId(id)
    scene.onPickCountry = (cc) => { setCountry(cc); setCityId('') }
    ;(async () => {
      const data = await api<Overview>('/stats/overview')
      setOv(data)
      await scene.loadCountries('/geo/europe.geojson', data.countries.map((c) => c.code))
      scene.setCities(data.cities)
      setLoading(null)
    })().catch((e) => setLoading(`Failed to load: ${e.message}`))
    return () => scene.dispose()
  }, [])

  useEffect(() => {
    const s = sceneRef.current
    if (!s) return
    s.showTotals = showTotals
    s.vegOnly = vegOnly
    s.applyBeaconMode()
    s.applyPinFilter()
  }, [showTotals, vegOnly])

  useEffect(() => {
    const s = sceneRef.current
    if (!s || !ov || cityId) return
    if (country) s.focusCountry(country)
    else s.focusEurope()
  }, [country, ov]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const s = sceneRef.current
    if (!s || !cityId || !ov) return
    const stat = ov.cities.find((c) => c.id === cityId)!
    if (country !== stat.country_code) setCountry(stat.country_code)
    setLookup(null)
    setLoading(`Loading ${stat.name} cityscape (OpenStreetMap buildings)…`)
    let cancelled = false
    ;(async () => {
      const pts = await api<{ points: any[] }>(`/stats/city/${cityId}`)
      let b: any = null
      try {
        b = await api(`/stats/city/${cityId}/buildings`)
      } catch { /* buildings optional */ }
      if (cancelled) return
      await s.enterCity(stat, pts.points, b)
      setCityInfo({ points: pts.points.length, veg: pts.points.filter((p) => p[4] >= 2).length, buildings: b?.buildings?.length || 0 })
      setLoading(null)
    })().catch((e) => setLoading(`Failed: ${e.message}`))
    return () => { cancelled = true }
  }, [cityId]) // eslint-disable-line react-hooks/exhaustive-deps

  const backToEurope = () => {
    setCityId('')
    setCityInfo(null)
    sceneRef.current?.exitCity()
    if (country) sceneRef.current?.focusCountry(country)
    else sceneRef.current?.focusEurope()
  }

  const doLookup = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!q.trim()) return
    setLookupErr('')
    setLookup(null)
    setLoading(`Checking “${q}” on OpenStreetMap…`)
    try {
      const r = await api<Lookup>(`/stats/lookup?q=${encodeURIComponent(q)}`)
      if (r.in_catalog && r.id) {
        setCityId(r.id)
      } else {
        setCityId('')
        setCityInfo(null)
        sceneRef.current?.showLookup(r.lat, r.lon, r.total)
        setLoading(null)
      }
      setLookup(r)
    } catch (err: any) {
      setLookupErr(err.message)
      setLoading(null)
    }
  }

  const cities = useMemo(() => (ov?.cities || []).filter((c) => !country || c.country_code === country), [ov, country])
  const selCountry = ov?.countries.find((c) => c.code === country)
  const selCity = ov?.cities.find((c) => c.id === cityId)
  const maxCountry = Math.max(...(ov?.countries.map((c) => (vegOnly ? c.veg_tagged : c.total)) || [1]))

  return (
    <div className="stats-layout">
      <div className="card map-wrap">
        <div ref={host} style={{ position: 'absolute', inset: 0 }} />
        <div className="map-overlay">
          {cityId ? (
            <button className="btn sm" onClick={backToEurope}><ArrowLeft size={14} /> Back to {selCountry?.name || 'Europe'}</button>
          ) : (
            <button className={`btn sm ${showTotals ? 'primary' : ''}`} onClick={() => setShowTotals(!showTotals)}>
              <Lightbulb size={14} /> {showTotals ? 'Hide' : 'Show'} total restaurants
            </button>
          )}
          <button className={`btn sm ${vegOnly ? 'primary' : ''}`} onClick={() => setVegOnly(!vegOnly)}><Leaf size={14} /> Vegetarian only</button>
          <select className="select" value={country} onChange={(e) => { setCityId(''); setCityInfo(null); sceneRef.current?.exitCity(); setCountry(e.target.value) }}>
            <option value="">All Europe</option>
            {ov?.countries.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
          </select>
          <select className="select" value={cityId} onChange={(e) => setCityId(e.target.value)}>
            <option value="">Select city…</option>
            {cities.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <form onSubmit={doLookup} className="row" style={{ gap: 6 }}>
            <input className="select" placeholder="Check any town…" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 150 }} />
            <button className="btn sm" aria-label="Check town"><Search size={14} /></button>
          </form>
          <span className="spacer" />
          <button className="btn sm" onClick={() => sceneRef.current?.zoom(0.7)} aria-label="Zoom in"><Plus size={14} /></button>
          <button className="btn sm" onClick={() => sceneRef.current?.zoom(1.4)} aria-label="Zoom out"><Minus size={14} /></button>
        </div>
        <div className="map-legend">
          {cityId ? (
            <>
              <div className="row" style={{ gap: 6 }}><span className="status-dot on" style={{ background: '#10ff9a' }} /> 100% vegetarian / vegan</div>
              <div className="row" style={{ gap: 6 }}><span className="status-dot" style={{ background: '#34d399' }} /> Vegetarian options</div>
              <div className="row" style={{ gap: 6 }}><span className="status-dot" style={{ background: '#fbbf24' }} /> Veg-friendly cuisine</div>
              <div className="row" style={{ gap: 6 }}><span className="status-dot" style={{ background: '#64748b' }} /> Other</div>
              <div className="faint">Drag to orbit · scroll to zoom · right-drag to pan</div>
            </>
          ) : (
            <>
              <div className="row" style={{ gap: 6 }}><span className="status-dot on" /> Beacon height = {vegOnly ? 'veg-tagged places' : 'restaurant count'} (log)</div>
              <div className="faint">Click a country to zoom · click a beacon for the 3D city</div>
            </>
          )}
        </div>
        {hover && (
          <div className="map-tip" style={{ left: hover.x, top: hover.y }}>
            <b>{hover.title}</b>
            {hover.lines.map((l, i) => <div key={i} className="muted">{l}</div>)}
          </div>
        )}
        {loading && <div className="map-loading"><div className="row"><Sparkles size={16} color="var(--green)" /> {loading}</div></div>}
      </div>

      <div className="grid" style={{ alignContent: 'start' }}>
        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <div className="card stat-tile"><div className="v">{ov ? (selCity?.total ?? selCountry?.total ?? ov.total).toLocaleString() : '—'}</div><div className="l">restaurants {selCity ? `in ${selCity.name}` : selCountry ? `in ${selCountry.name}` : 'in Europe'}</div></div>
          <div className="card stat-tile"><div className="v" style={{ color: 'var(--green)' }}>{ov ? (selCity?.veg_tagged ?? selCountry?.veg_tagged ?? ov.veg_tagged).toLocaleString() : '—'}</div><div className="l">tagged vegetarian / vegan</div></div>
        </div>

        {lookup && !lookup.in_catalog && (
          <div className="card section fade-in">
            <h3><Search size={16} /> {lookup.name}{lookup.country ? `, ${lookup.country}` : ''}</h3>
            <div className={`chip ${lookup.total ? 'green' : 'red'}`}>{lookup.total ? `${lookup.total} places found within ~2 km` : 'No restaurants found nearby'}</div>
            <p className="muted" style={{ fontSize: 13 }}>{lookup.veg_tagged} tagged vegetarian/vegan. Live count from OpenStreetMap — this town is not in the agent's catalog yet, so recommendations are not available.</p>
            {!!lookup.sample?.length && <div className="faint" style={{ fontSize: 12.5 }}>e.g. {lookup.sample.join(' · ')}</div>}
          </div>
        )}
        {lookupErr && <div className="chip red">{lookupErr}</div>}

        {selCity && cityInfo && (
          <div className="card section fade-in">
            <h3><Building2 size={16} /> {selCity.name} in 3D</h3>
            <div className="grid" style={{ gap: 6, fontSize: 13.5 }}>
              <div className="row"><span className="muted">Places on map</span><span className="spacer" />{cityInfo.points.toLocaleString()}</div>
              <div className="row"><span className="muted">Veg-tagged</span><span className="spacer" />{cityInfo.veg}</div>
              <div className="row"><span className="muted">Breakfast spots</span><span className="spacer" />{selCity.breakfast}</div>
              <div className="row"><span className="muted">3D buildings</span><span className="spacer" />{cityInfo.buildings.toLocaleString()}</div>
            </div>
            <button className="btn primary" style={{ marginTop: 14, width: '100%' }}
              onClick={() => nav(`/app/dashboard?q=${encodeURIComponent(`Vegetarian breakfast, lunch and dinner in ${selCity.name}`)}`)}>
              <Sparkles size={15} /> Ask the agent about {selCity.name}
            </button>
          </div>
        )}

        <div className="card section">
          <h3><Globe2 size={16} /> {country ? `Cities in ${selCountry?.name}` : 'By country'}</h3>
          {country
            ? cities.map((c) => (
              <div key={c.id} className="bar-row">
                <button onClick={() => setCityId(c.id)}>{c.name}</button>
                <div className="bar"><div style={{ width: `${(100 * (vegOnly ? c.veg_tagged : c.total)) / Math.max(...cities.map((x) => (vegOnly ? x.veg_tagged : x.total)), 1)}%` }} /></div>
                <span className="mono" style={{ textAlign: 'right' }}>{(vegOnly ? c.veg_tagged : c.total).toLocaleString()}</span>
              </div>
            ))
            : ov?.countries.map((c) => (
              <div key={c.code} className="bar-row">
                <button onClick={() => setCountry(c.code)}>{c.name}</button>
                <div className="bar"><div style={{ width: `${(100 * (vegOnly ? c.veg_tagged : c.total)) / maxCountry}%` }} /></div>
                <span className="mono" style={{ textAlign: 'right' }}>{(vegOnly ? c.veg_tagged : c.total).toLocaleString()}</span>
              </div>
            ))}
        </div>

        {!country && ov && (
          <div className="card section">
            <h3>Top cuisines</h3>
            <div className="row wrap" style={{ gap: 6 }}>
              {ov.top_cuisines.map((c) => <span key={c.cuisine} className="chip">{c.cuisine} · {c.n.toLocaleString()}</span>)}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
