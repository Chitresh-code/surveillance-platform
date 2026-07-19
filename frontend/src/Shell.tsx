import type { ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { clearToken, getUsername } from './auth'
import { LiveFeed } from './LiveFeed'

const NAV_LINKS = [
  { to: '/', label: 'Map', end: true },
  { to: '/cameras', label: 'Cameras', end: false },
  { to: '/identities', label: 'Identities', end: false },
  { to: '/audit-log', label: 'Audit log', end: false },
]

export function Shell({ children }: { children: ReactNode }) {
  const navigate = useNavigate()

  function handleLogout() {
    clearToken()
    navigate('/login', { replace: true })
  }

  return (
    <div className="shell">
      <div className="scanlines" aria-hidden="true" />
      <aside className="shell-sidebar">
        <div>
          <div className="shell-brand">&gt;_ SURVEILLANCE</div>
          <div className="shell-operator">operator: {getUsername() ?? 'unknown'}</div>
        </div>
        <nav className="shell-nav">
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => `shell-nav-link${isActive ? ' active' : ''}`}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <LiveFeed />
        <button className="shell-logout" onClick={handleLogout} type="button">
          Log out
        </button>
      </aside>
      <main className="shell-main">{children}</main>
    </div>
  )
}
