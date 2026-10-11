import { useCallback, useRef, useState } from 'react'
import { streamAgent, type AgentEvent, type City, type Recommendation, type StepEvent } from '../api'

export type RunState = {
  running: boolean
  steps: StepEvent[]
  answer: string
  answering: boolean
  results: Record<string, Recommendation[]> | null
  city: City | null
  intent: any
  clarify: string | null
  error: string | null
  elapsed: number | null
}

const EMPTY: RunState = {
  running: false, steps: [], answer: '', answering: false, results: null, city: null,
  intent: null, clarify: null, error: null, elapsed: null,
}

export function useAgentRun() {
  const [state, setState] = useState<RunState>(EMPTY)
  const abort = useRef<AbortController | null>(null)

  const run = useCallback(async (query: string, overrides: Record<string, any> = {}) => {
    abort.current?.abort()
    const ctrl = new AbortController()
    abort.current = ctrl
    setState({ ...EMPTY, running: true })
    const onEvent = (e: AgentEvent) => {
      setState((s) => {
        switch (e.type) {
          case 'step': {
            const idx = s.steps.findIndex((x) => x.step === e.step)
            const steps = [...s.steps]
            if (idx >= 0) steps[idx] = e
            else steps.push(e)
            return { ...s, steps }
          }
          case 'results':
            return { ...s, results: e.recommendations, city: e.city, intent: e.intent }
          case 'answer_start':
            return { ...s, answering: true }
          case 'token':
            return { ...s, answer: s.answer + e.text }
          case 'clarify':
            return { ...s, clarify: e.message }
          case 'error':
            return { ...s, error: e.message, running: false }
          case 'done':
            return { ...s, running: false, answering: false, elapsed: e.elapsed }
        }
        return s
      })
    }
    try {
      await streamAgent({ query, overrides }, onEvent, ctrl.signal)
    } catch (err: any) {
      if (err.name !== 'AbortError') setState((s) => ({ ...s, error: err.message, running: false }))
    } finally {
      setState((s) => ({ ...s, running: false, answering: false }))
    }
  }, [])

  const reset = useCallback(() => {
    abort.current?.abort()
    setState(EMPTY)
  }, [])

  return { state, run, reset }
}
