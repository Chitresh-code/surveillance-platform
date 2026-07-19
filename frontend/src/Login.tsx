import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from './api'

export function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await login(username, password)
      navigate('/', { replace: true })
    } catch {
      setError('Incorrect username or password.')
    }
  }

  return (
    <div className="login">
      <form className="login-form" onSubmit={handleSubmit}>
        <h1>Surveillance Platform</h1>
        <label>
          Username
          <input value={username} onChange={(event) => setUsername(event.target.value)} autoFocus />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error && <span className="login-error">{error}</span>}
        <button type="submit">Log in</button>
      </form>
    </div>
  )
}
