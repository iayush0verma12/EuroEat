import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { ArrowRight, Eye, EyeOff, Languages, Lock, MessageSquareQuote, ShieldCheck, User, UtensilsCrossed } from 'lucide-react'
import { useAuth } from '../auth'

export default function Login() {
  const { user, login } = useAuth()
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [remember, setRemember] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [shake, setShake] = useState(false)

  if (user) return <Navigate to="/app/dashboard" replace />

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(username, password, remember)
      nav('/app/dashboard')
    } catch (err: any) {
      setError(err.status === 401 ? 'Incorrect login ID or password.' : 'Unable to sign in right now. Please try again.')
      setShake(true)
      setTimeout(() => setShake(false), 450)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <section className="login-hero">
        <div className="brand" style={{ padding: 0 }}>
          <div className="brand-logo"><UtensilsCrossed size={19} /></div>
          <div>EuroEat<small>Restaurant intelligence for travellers</small></div>
        </div>

        <div>
          <div className="eyebrow">AI dining concierge · Europe</div>
          <h1>Know what to eat<br />before you arrive.</h1>
          <p className="lead">
            EuroEat finds the right restaurants for your trip, reads and translates their menus, weighs what diners
            say, and recommends exactly what to order — with prices.
          </p>

          <div className="hero-stats">
            <div><b>84k+</b><span>restaurants</span></div>
            <div><b>32</b><span>cities</span></div>
            <div><b>18</b><span>countries</span></div>
          </div>

          <div className="feature-list">
            <div className="feature"><Languages size={17} /><span><b>Menus in your language.</b> Dishes and prices read from restaurant websites and translated.</span></div>
            <div className="feature"><MessageSquareQuote size={17} /><span><b>Reviews that matter to you.</b> Diet, allergies, kids or budget — surfaced from diner feedback.</span></div>
            <div className="feature"><ShieldCheck size={17} /><span><b>Private by design.</b> Language models run locally; your searches stay on your machine.</span></div>
          </div>
        </div>

        <div className="hero-foot faint">Map data © OpenStreetMap contributors</div>
      </section>

      <section className="login-panel">
        <form className={`card login-card ${shake ? 'shake' : ''}`} onSubmit={submit} noValidate>
          <h2>Sign in</h2>
          <p className="muted login-sub">Welcome back. Enter your details to continue.</p>

          <div className="grid" style={{ gap: 16 }}>
            <label className="field">
              Login ID
              <div className="input-icon">
                <User size={16} />
                <input className="input" value={username} autoFocus
                  onChange={(e) => setUsername(e.target.value)} placeholder="Enter your login ID" autoComplete="username" />
              </div>
            </label>
            <label className="field">
              Password
              <div className="input-icon">
                <Lock size={16} />
                <input className="input" type={showPw ? 'text' : 'password'} value={password} style={{ paddingRight: 44 }}
                  onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" autoComplete="current-password" />
                <button type="button" className="pw-toggle" onClick={() => setShowPw(!showPw)}
                  aria-label={showPw ? 'Hide password' : 'Show password'}>
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </label>

            <div className="row" style={{ fontSize: 13 }}>
              <label className="check">
                <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
                Keep me signed in
              </label>
              <span className="spacer" />
              <span className="faint" title="Contact your administrator to reset your password." style={{ cursor: 'help' }}>
                Forgot password?
              </span>
            </div>

            {error && <div className="form-error" role="alert">{error}</div>}

            <button className="btn primary lg" disabled={busy || !username || !password}>
              {busy ? 'Signing in…' : <>Sign in <ArrowRight size={16} /></>}
            </button>
          </div>
        </form>
        <div className="login-legal faint">
          © {new Date().getFullYear()} EuroEat · Secure sign-in
        </div>
      </section>
    </div>
  )
}
