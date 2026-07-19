import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchMapActivity, fetchMapCameras, type MapActivity, type MapCamera } from './api'
import { clearToken } from './auth'
import { MapView } from './MapView'

const POLL_INTERVAL_MS = 10_000

export function MapPage() {
  const [cameras, setCameras] = useState<MapCamera[]>([])
  const [activity, setActivity] = useState<MapActivity[]>([])
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [camerasRes, activityRes] = await Promise.all([fetchMapCameras(), fetchMapActivity()])
        if (cancelled) return
        setCameras(camerasRes.data)
        setActivity(activityRes.data)
        setError(null)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load map data')
      }
    }

    load()
    const interval = setInterval(load, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  function handleLogout() {
    clearToken()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Surveillance Map</h1>
        {error && <span className="app-error">{error}</span>}
        <button className="app-logout" onClick={handleLogout} type="button">
          Log out
        </button>
      </header>
      <main className="app-map">
        <MapView cameras={cameras} activity={activity} />
      </main>
    </div>
  )
}
