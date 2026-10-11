import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRight, BarChart3, Compass, Search, X } from 'lucide-react'
import { useAgentRun } from '../hooks/useAgentRun'
import RunView from '../components/RunView'

const EXAMPLES = [
  'Vegetarian breakfast, lunch and dinner in Barcelona',
  'Vegan dinner in Berlin, somewhere quiet',
  'Cheap veg lunch in Paris, I am gluten intolerant',
  'Breakfast in Lisbon with kids',
  'What should a vegetarian try in Rome?',
]

export default function Dashboard() {
  const [q, setQ] = useState('')
  const { state, run, reset } = useAgentRun()
  const nav = useNavigate()
  const [params, setParams] = useSearchParams()
  const active = state.running || state.steps.length > 0

  useEffect(() => {
    const preset = params.get('q')
    if (preset) {
      setParams({}, { replace: true })
      setQ(preset)
      run(preset)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const submit = (text = q) => {
    if (!text.trim()) return
    setQ(text)
    run(text)
  }

  return (
    <div>
      <section className={`search-hero ${active ? 'compact' : ''}`}>
        {!active && (
          <>
            <div className="logo-big">
              <span className="gradient-text">Euro</span>Eat
            </div>
            <p className="muted" style={{ marginBottom: 26, fontSize: 15.5 }}>
              Ask for a city, a meal and your diet — the agent does the rest.
            </p>
          </>
        )}
        <form className="search-box" onSubmit={(e) => { e.preventDefault(); submit() }}>
          <Search size={20} color="var(--faint)" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Vegetarian lunch and dinner in Barcelona, gluten-free" aria-label="Ask the agent" />
          {q && <button type="button" className="btn ghost sm" onClick={() => { setQ(''); reset() }} aria-label="Clear"><X size={16} /></button>}
          <button className="icon-btn" aria-label="Search"><ArrowRight size={20} /></button>
        </form>
        {!active && (
          <>
            <div className="suggestions">
              {EXAMPLES.map((e) => <button key={e} className="suggestion" onClick={() => submit(e)}>{e}</button>)}
            </div>
            <div className="hero-actions">
              <button className="btn lg primary" onClick={() => nav('/app/assisted')}><Compass size={18} /> Assisted search</button>
              <button className="btn lg" onClick={() => nav('/app/stats')}><BarChart3 size={18} /> Stats · 3D map</button>
            </div>
          </>
        )}
      </section>
      {active && <RunView state={state} />}
    </div>
  )
}
