import { BookOpen, Brain, Check, Filter, Languages, ListChecks, Loader2, MessageSquareText, Search, Sparkles, Target } from 'lucide-react'
import type { StepEvent } from '../api'

const META: Record<string, { label: string; icon: any }> = {
  understand: { label: '1 · Understand', icon: Brain },
  identify: { label: '2 · Identify', icon: Search },
  shortlist: { label: '3 · Shortlist', icon: Filter },
  read_menu: { label: '4 · Read menus', icon: BookOpen },
  translate: { label: '5 · Translate', icon: Languages },
  reviews: { label: '6 · Reviews (+/−)', icon: MessageSquareText },
  context: { label: '7 · Context search', icon: Target },
  menu_items: { label: '8 · Menu items & prices', icon: ListChecks },
  suggest: { label: '9 · Suggest', icon: Sparkles },
}
const ORDER = Object.keys(META)

function StepData({ s }: { s: StepEvent }) {
  const d = s.data || {}
  if (s.step === 'shortlist' && d.shortlist) {
    return (
      <div className="step-data">
        {Object.entries(d.shortlist as Record<string, any[]>).map(([meal, list]) => (
          <div key={meal} className="kv" style={{ display: 'block' }}>
            <span className="k">{meal}: </span>
            {list.map((r) => r.name).join(' · ')}
          </div>
        ))}
      </div>
    )
  }
  if (s.step === 'read_menu' && d.menus) {
    return (
      <div className="step-data">
        {Object.entries(d.menus as Record<string, any>).slice(0, 12).map(([name, m]) => (
          <div key={name} className="kv">
            <span className={`chip ${m.source === 'scraped' ? 'green' : 'amber'}`} style={{ padding: '0 6px' }}>
              {m.source}
            </span>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {m.page ? <a href={m.page} target="_blank" rel="noreferrer">{name}</a> : name} · {m.items}
            </span>
          </div>
        ))}
      </div>
    )
  }
  if (s.step === 'translate' && d.examples?.length) {
    return (
      <div className="step-data">
        {d.examples.slice(0, 5).map((e: any, i: number) => (
          <div key={i} className="kv" style={{ display: 'block' }}>
            <span className="k" style={{ fontStyle: 'italic' }}>{e.original}</span> → {e.english}
          </div>
        ))}
      </div>
    )
  }
  if (s.step === 'reviews' && (d.positive_sample || d.negative_sample)) {
    return (
      <div className="step-data">
        {d.positive_sample && (
          <div className="kv" style={{ display: 'block', borderLeft: '3px solid var(--green)' }}>
            {d.positive_sample.text_en}
          </div>
        )}
        {d.negative_sample && (
          <div className="kv" style={{ display: 'block', borderLeft: '3px solid var(--red)' }}>
            {d.negative_sample.text_en}
          </div>
        )}
      </div>
    )
  }
  return null
}

export default function AgentTrace({ steps, running, elapsed }: { steps: StepEvent[]; running: boolean; elapsed: number | null }) {
  const sorted = [...steps].sort((a, b) => ORDER.indexOf(a.step) - ORDER.indexOf(b.step))
  return (
    <div className="card trace">
      <h3>
        <Brain size={17} color="var(--green)" /> Agent reasoning
        <span className="spacer" />
        {running ? <span className="chip amber">working…</span> : elapsed != null && <span className="chip green">{elapsed}s</span>}
      </h3>
      {sorted.map((s) => {
        const m = META[s.step] || { label: s.step, icon: Sparkles }
        const Icon = s.status === 'done' ? Check : s.status === 'running' ? Loader2 : m.icon
        return (
          <div key={s.step} className={`step ${s.status} fade-in`}>
            <div className="step-icon"><Icon size={14} /></div>
            <div>
              <div className="step-label">{m.label}</div>
              <div className="step-title">{s.title}</div>
              {s.detail && <div className="step-detail">{s.detail}</div>}
              {s.status === 'done' && <StepData s={s} />}
            </div>
          </div>
        )
      })}
      {!sorted.length && <div className="muted" style={{ fontSize: 13 }}>Starting…</div>}
    </div>
  )
}
