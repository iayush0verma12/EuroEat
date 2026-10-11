import { useEffect, useRef } from 'react'

type P = { x: number; y: number; vx: number; vy: number; life: number; max: number; size: number; hue: number; star: boolean }

/** Full-screen canvas: sparkle trail on mouse move, burst + ripple on click. */
export default function SparkleCursor({ enabled = true }: { enabled?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!enabled) return
    const canvas = ref.current!
    const ctx = canvas.getContext('2d')!
    const parts: P[] = []
    const ripples: { x: number; y: number; r: number; a: number }[] = []
    let raf = 0
    let last = { x: -1, y: -1 }
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const resize = () => {
      canvas.width = window.innerWidth * dpr
      canvas.height = window.innerHeight * dpr
      canvas.style.width = window.innerWidth + 'px'
      canvas.style.height = window.innerHeight + 'px'
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()

    const spawn = (x: number, y: number, n: number, speed: number) => {
      for (let i = 0; i < n; i++) {
        const a = Math.random() * Math.PI * 2
        const s = Math.random() * speed
        parts.push({
          x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s - 0.3,
          life: 0, max: 30 + Math.random() * 30, size: 0.8 + Math.random() * 1.8,
          hue: Math.random() < 0.6 ? 150 + Math.random() * 30 : 40 + Math.random() * 15,
          star: Math.random() < 0.35,
        })
      }
    }

    const onMove = (e: PointerEvent) => {
      const d = Math.hypot(e.clientX - last.x, e.clientY - last.y)
      last = { x: e.clientX, y: e.clientY }
      spawn(e.clientX, e.clientY, Math.min(2, Math.floor(d / 16)), 0.9)
    }
    const onDown = (e: PointerEvent) => {
      spawn(e.clientX, e.clientY, 14, 3)
      ripples.push({ x: e.clientX, y: e.clientY, r: 4, a: 0.4 })
    }

    const drawStar = (x: number, y: number, r: number) => {
      ctx.beginPath()
      for (let i = 0; i < 4; i++) {
        const a = (i * Math.PI) / 2
        ctx.moveTo(x, y)
        ctx.lineTo(x + Math.cos(a) * r * 2.4, y + Math.sin(a) * r * 2.4)
      }
      ctx.stroke()
    }

    const tick = () => {
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)
      ctx.globalCompositeOperation = 'lighter'
      for (let i = parts.length - 1; i >= 0; i--) {
        const p = parts[i]
        p.life++
        p.x += p.vx
        p.y += p.vy
        p.vy += 0.025
        p.vx *= 0.98
        const t = 1 - p.life / p.max
        if (t <= 0) {
          parts.splice(i, 1)
          continue
        }
        const color = `hsla(${p.hue}, 90%, 65%, ${t})`
        ctx.fillStyle = color
        ctx.strokeStyle = color
        ctx.lineWidth = 1
        if (p.star) drawStar(p.x, p.y, p.size * t)
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size * t, 0, Math.PI * 2)
        ctx.fill()
      }
      for (let i = ripples.length - 1; i >= 0; i--) {
        const r = ripples[i]
        r.r += 2.2
        r.a *= 0.94
        if (r.a < 0.02) {
          ripples.splice(i, 1)
          continue
        }
        ctx.strokeStyle = `hsla(155, 80%, 60%, ${r.a})`
        ctx.lineWidth = 1.5
        ctx.beginPath()
        ctx.arc(r.x, r.y, r.r, 0, Math.PI * 2)
        ctx.stroke()
      }
      ctx.globalCompositeOperation = 'source-over'
      raf = requestAnimationFrame(tick)
    }

    if (!reduce) {
      window.addEventListener('pointermove', onMove)
      window.addEventListener('pointerdown', onDown)
      raf = requestAnimationFrame(tick)
    }
    window.addEventListener('resize', resize)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerdown', onDown)
      window.removeEventListener('resize', resize)
    }
  }, [enabled])

  if (!enabled) return null
  return <canvas ref={ref} className="sparkle-canvas" aria-hidden />
}
