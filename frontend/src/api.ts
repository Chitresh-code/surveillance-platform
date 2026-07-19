const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export interface MapCamera {
  id: string
  name: string
  lat: number
  lon: number
  status: string
}

export interface MapActivity {
  id: string
  identity_id: string
  camera_id: string
  lat: number
  lon: number
  seen_at: string
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    throw new Error(`${path} failed: ${response.status}`)
  }
  return response.json()
}

export function fetchMapCameras(): Promise<{ data: MapCamera[] }> {
  return get('/map/cameras')
}

export function fetchMapActivity(): Promise<{ data: MapActivity[] }> {
  return get('/map/activity')
}
