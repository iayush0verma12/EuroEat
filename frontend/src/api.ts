export type MenuItem = {
  name: string
  name_en?: string
  price: number
  currency: string
  vegetarian?: boolean
  meal?: string
}

export type Review = {
  author: string
  rating: number
  lang: string
  text: string
  text_en: string
  source: string
  created_at: string
  query?: string
  similarity?: number | null
}

export type Links = { website?: string | null; menu?: string | null; osm: string; google_maps: string }

export type Recommendation = {
  id: string
  name: string
  cuisine: string | null
  amenity: string
  address: string | null
  lat: number
  lon: number
  phone: string | null
  opening_hours: string | null
  veg_tag: string | null
  vegan_tag: string | null
  price_level: number
  rating: number | null
  review_count: number
  links: Links
  menu: { source: 'scraped' | 'estimated'; note: string; lang: string; pdf?: string | null; items: MenuItem[] }
  avg_price: number | null
  currency: string
  positive: Review[]
  negative: Review[]
  context_matches: Review[]
  score: number
  distance_km: number
}

export type City = {
  id: string
  name: string
  country_code: string
  country: string
  lat: number
  lon: number
  lang: string
  currency: string
  bbox: number[]
  restaurants?: number
  veg_tagged?: number
}

export type StepEvent = {
  type: 'step'
  step: string
  status: 'running' | 'done'
  title: string
  detail: string
  data: Record<string, any>
}

export type AgentEvent =
  | StepEvent
  | { type: 'results'; city: City; intent: any; recommendations: Record<string, Recommendation[]> }
  | { type: 'answer_start' }
  | { type: 'token'; text: string }
  | { type: 'clarify'; message: string }
  | { type: 'error'; message: string }
  | { type: 'done'; elapsed: number }

const TOKEN_KEY = 'euroeat.token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

/** persist=true keeps the session across browser restarts ("Keep me signed in"). */
export function setToken(t: string | null, persist = true) {
  try {
    localStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(TOKEN_KEY)
    if (t) (persist ? localStorage : sessionStorage).setItem(TOKEN_KEY, t)
  } catch {
    /* storage unavailable */
  }
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: any } = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: opts.method || (opts.body ? 'POST' : 'GET'),
    headers: {
      'Content-Type': 'application/json',
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })
  if (res.status === 401 && path !== '/auth/login') {
    setToken(null)
    window.location.href = '/login'
  }
  if (!res.ok) {
    let msg = res.statusText
    try {
      msg = (await res.json()).detail || msg
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, msg)
  }
  return res.json()
}

/** POSTs to the agent and calls onEvent for every server-sent event. */
export async function streamAgent(
  body: { query: string; overrides?: Record<string, any> },
  onEvent: (e: AgentEvent) => void,
  signal?: AbortSignal,
) {
  const res = await fetch('/api/agent/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) throw new ApiError(res.status, 'Agent request failed')
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      const line = chunk.split('\n').find((l) => l.startsWith('data: '))
      if (line) onEvent(JSON.parse(line.slice(6)))
    }
  }
}
