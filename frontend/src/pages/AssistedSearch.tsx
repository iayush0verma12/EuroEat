import { useEffect, useState } from 'react'
import { ArrowLeft, Bot, Check, Coffee, Drumstick, Leaf, Moon, RotateCcw, Sprout, Sun } from 'lucide-react'
import { api, type City } from '../api'
import { useAgentRun } from '../hooks/useAgentRun'
import RunView from '../components/RunView'

type Country = { code: string; name: string; cities: number; restaurants: number }

const FLAG = (cc: string) => String.fromCodePoint(...[...cc.toUpperCase()].map((c) => 0x1f1a5 + c.charCodeAt(0)))

const DIETS = [
  { id: 'vegetarian', t: 'Vegetarian', s: 'No meat or fish', icon: Leaf },
  { id: 'vegan', t: 'Vegan', s: 'Plant-based only', icon: Sprout },
  { id: 'any', t: 'Non-veg', s: 'Everything on the menu', icon: Drumstick },
]
const MEALS = [
  { id: 'breakfast', t: 'Breakfast', s: 'Cafés & bakeries', icon: Coffee },
  { id: 'lunch', t: 'Lunch', s: 'Set menus & bistros', icon: Sun },
  { id: 'dinner', t: 'Dinner', s: 'Restaurants open late', icon: Moon },
]

export default function AssistedSearch() {
  const [step, setStep] = useState(0)
  const [countries, setCountries] = useState<Country[]>([])
  const [cities, setCities] = useState<City[]>([])
  const [country, setCountry] = useState<Country | null>(null)
  const [city, setCity] = useState<City | null>(null)
  const [diet, setDiet] = useState<string | null>(null)
  const [meals, setMeals] = useState<string[]>([])
  const { state, run, reset } = useAgentRun()

  useEffect(() => {
    api<Country[]>('/countries').then(setCountries)
  }, [])
  useEffect(() => {
    if (country) api<City[]>(`/cities?country=${country.code}`).then(setCities)
  }, [country])

  const go = () => {
    setStep(4)
    run('', { city: city!.id, diet, meals, is_restaurant_search: true })
  }
  const restart = () => {
    reset()
    setStep(0)
    setCountry(null)
    setCity(null)
    setDiet(null)
    setMeals([])
  }

  const questions = [
    'Where do you want to travel in Europe? Pick a country first.',
    `Great — which city in ${country?.name}?`,
    'What do you prefer to eat?',
    'Which meals should I plan? Pick one or more.',
  ]

  return (
    <div className={step < 4 ? 'wizard' : ''}>
      <div className="progress">{[0, 1, 2, 3, 4].map((i) => <div key={i} className={i <= step ? 'on' : ''} />)}</div>

      <div className="answers">
        {country && <span className="chip green">{FLAG(country.code)} {country.name}</span>}
        {city && <span className="chip green">{city.name}</span>}
        {diet && step > 2 && <span className="chip green">{DIETS.find((d) => d.id === diet)?.t}</span>}
        {meals.length > 0 && step > 3 && <span className="chip green">{meals.join(' · ')}</span>}
        <span className="spacer" />
        {step > 0 && step < 4 && <button className="btn sm ghost" onClick={() => setStep(step - 1)}><ArrowLeft size={14} /> Back</button>}
        {step > 0 && <button className="btn sm ghost" onClick={restart}><RotateCcw size={14} /> Start over</button>}
      </div>

      {step < 4 && (
        <div className="bubble fade-in" key={step}>
          <div className="bot"><Bot size={20} /></div>
          <div className="msg">{questions[step]}</div>
        </div>
      )}

      {step === 0 && (
        <div className="choice-grid fade-in">
          {countries.map((c) => (
            <button key={c.code} className={`choice ${country?.code === c.code ? 'on' : ''}`}
              onClick={() => { setCountry(c); setCity(null); setStep(1) }}>
              <span className="big">{FLAG(c.code)}</span>
              <span className="t">{c.name}</span>
              <span className="s">{c.cities} cities · {c.restaurants.toLocaleString()} places</span>
            </button>
          ))}
        </div>
      )}

      {step === 1 && (
        <div className="choice-grid fade-in">
          {cities.map((c) => (
            <button key={c.id} className={`choice ${city?.id === c.id ? 'on' : ''}`} disabled={!c.restaurants}
              onClick={() => { setCity(c); setStep(2) }}>
              <span className="t">{c.name}</span>
              <span className="s">{c.restaurants ? `${c.restaurants.toLocaleString()} places · ${c.veg_tagged} veg-tagged` : 'not ingested yet'}</span>
            </button>
          ))}
        </div>
      )}

      {step === 2 && (
        <div className="choice-grid fade-in">
          {DIETS.map((d) => (
            <button key={d.id} className={`choice ${diet === d.id ? 'on' : ''}`} onClick={() => { setDiet(d.id); setStep(3) }}>
              <d.icon size={26} color={d.id === 'any' ? 'var(--amber)' : 'var(--green)'} />
              <span className="t">{d.t}</span>
              <span className="s">{d.s}</span>
            </button>
          ))}
        </div>
      )}

      {step === 3 && (
        <>
          <div className="choice-grid fade-in">
            {MEALS.map((m) => {
              const on = meals.includes(m.id)
              return (
                <button key={m.id} className={`choice ${on ? 'on' : ''}`}
                  onClick={() => setMeals(on ? meals.filter((x) => x !== m.id) : [...meals, m.id])}>
                  {on && <Check size={18} className="tick" />}
                  <m.icon size={26} color="var(--amber)" />
                  <span className="t">{m.t}</span>
                  <span className="s">{m.s}</span>
                </button>
              )
            })}
          </div>
          <div className="row" style={{ marginTop: 22, justifyContent: 'flex-end' }}>
            <button className="btn primary lg" disabled={!meals.length} onClick={go}><Bot size={18} /> Find restaurants</button>
          </div>
        </>
      )}

      {step === 4 && <RunView state={state} />}
    </div>
  )
}
