import { useEffect, useState } from 'react'
import { AlertTriangle, Coffee, Moon, Sparkles, Sun } from 'lucide-react'
import type { RunState } from '../hooks/useAgentRun'
import AgentTrace from './AgentTrace'
import Markdown from './Markdown'
import RestaurantCard from './RestaurantCard'

const MEAL_ICON: Record<string, any> = { breakfast: Coffee, lunch: Sun, dinner: Moon }

export default function RunView({ state }: { state: RunState }) {
  const meals = state.results ? Object.keys(state.results) : []
  const [meal, setMeal] = useState<string | null>(null)
  useEffect(() => {
    if (meals.length && (!meal || !meals.includes(meal))) setMeal(meals[0])
  }, [meals.join(',')]) // eslint-disable-line react-hooks/exhaustive-deps

  const diet = state.intent?.diet || 'vegetarian'
  return (
    <div className="run-layout">
      <AgentTrace steps={state.steps} running={state.running} elapsed={state.elapsed} />
      <div style={{ minWidth: 0 }}>
        {state.error && <div className="card answer" style={{ borderColor: 'var(--red)' }}><AlertTriangle size={16} color="var(--red)" /> {state.error}</div>}
        {state.clarify && <div className="card answer fade-in"><Sparkles size={16} color="var(--green)" /> {state.clarify}</div>}
        {(state.answering || state.answer) && (
          <div className="card answer fade-in">
            <div className="sub-h"><Sparkles size={13} /> Agent suggestion {state.city && `· ${state.city.name}`}</div>
            <div className={state.answering ? 'cursor-blink' : ''}><Markdown text={state.answer} /></div>
          </div>
        )}
        {!state.results && state.running && !state.answer && (
          <div className="card answer muted fade-in">
            The agent is working through the pipeline on the left — reading real menus can take a little while.
          </div>
        )}
        {state.results && (
          <>
            <div className="meal-tabs">
              {meals.map((m) => {
                const Icon = MEAL_ICON[m] || Sun
                return (
                  <button key={m} className={`meal-tab ${meal === m ? 'active' : ''}`} onClick={() => setMeal(m)}>
                    <Icon size={15} /> {m[0].toUpperCase() + m.slice(1)} <span style={{ opacity: .7 }}>{state.results![m].length}</span>
                  </button>
                )
              })}
            </div>
            <div className="rest-grid">
              {meal && state.results[meal]?.map((r, i) => <RestaurantCard key={r.id} r={r} rank={i} meal={meal} diet={diet} />)}
              {meal && !state.results[meal]?.length && <div className="card answer muted">No places found for {meal}.</div>}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
