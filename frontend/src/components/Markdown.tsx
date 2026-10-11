import { Fragment, type ReactNode } from 'react'

/** Minimal markdown renderer for LLM answers: headings, bold/italic, bullet lists, paragraphs. */
function inline(text: string): ReactNode[] {
  const out: ReactNode[] = []
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g
  let last = 0
  let m: RegExpExecArray | null
  let i = 0
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index))
    const tok = m[0]
    out.push(tok.startsWith('**') ? <b key={i++}>{tok.slice(2, -2)}</b> : <i key={i++}>{tok.slice(1, -1)}</i>)
    last = m.index + tok.length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

export default function Markdown({ text }: { text: string }) {
  const lines = text.split('\n')
  const blocks: ReactNode[] = []
  let list: string[] = []
  const flush = () => {
    if (list.length) {
      blocks.push(<ul key={blocks.length}>{list.map((l, i) => <li key={i}>{inline(l)}</li>)}</ul>)
      list = []
    }
  }
  for (const raw of lines) {
    const line = raw.trimEnd()
    if (/^\s*[-*+]\s+/.test(line)) {
      list.push(line.replace(/^\s*[-*+]\s+/, ''))
      continue
    }
    flush()
    if (!line.trim() || /^[=-]{3,}$/.test(line.trim())) continue
    const h = line.match(/^(#{1,4})\s+(.*)/)
    if (h) blocks.push(<h3 key={blocks.length}>{inline(h[2])}</h3>)
    else blocks.push(<p key={blocks.length}>{inline(line)}</p>)
  }
  flush()
  return <Fragment>{blocks}</Fragment>
}
