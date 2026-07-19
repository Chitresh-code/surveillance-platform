import { useEffect, useState } from 'react'
import { fetchMapActivity, fetchMapCameras, type MapActivity, type MapCamera } from './api'
import { MapView } from './MapView'

const POLL_INTERVAL_MS = 10_000

export function MapPage() {
  const [cameras, setCameras] = useState<MapCamera[]>([])
  const [activity, setActivity] = useState<MapActivity[]>([])
  const [error, setError] = useState<string | null>(null)

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

  return (
    <div className="map-page">
      <h1 className="page-title">[ Map ]</h1>
      {error && <div className="page-error">{error}</div>}
      <div className="map-frame">
        <MapView cameras={cameras} activity={activity} />
      </div>
    </div>
  )
}
