import { clearToken, getRefreshToken, getToken, setRefreshToken, setToken } from './auth'

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

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Camera {
  id: string
  name: string
  lat: number
  lon: number
  stream_url: string
  status: string
  created_at: string
}

export interface Identity {
  id: string
  first_seen: string
  last_seen: string
}

export interface Sighting {
  id: string
  identity_id: string
  track_id: string
  camera_id: string
  seen_at: string
  match_confidence: number
}

export interface AuditLogEntry {
  id: string
  operator_id: string
  action: string
  resource_type: string
  resource_id: string
  created_at: string
}

export interface SightingEvent {
  identity_id: string
  camera_id: string
  track_id: string
  seen_at: string
  match_confidence: number
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// ponytail: a session hard-expires at 12h (docs/DECISIONS.md ADR-0010) unless the
// access token is silently renewed first — this is that renewal, tried once per
// 401 before giving up and sending the operator back to /login (ADR-0013).
async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!response.ok) return false
  const body: LoginResponse = await response.json()
  setToken(body.access_token)
  setRefreshToken(body.refresh_token)
  return true
}

async function requestWithAuth(path: string, init: RequestInit): Promise<Response> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: { ...init.headers, ...authHeaders() } })
  if (response.status !== 401) return response
  if (!(await refreshAccessToken())) return response
  return fetch(`${API_BASE_URL}${path}`, { ...init, headers: { ...init.headers, ...authHeaders() } })
}

async function handleResponse<T>(response: Response, path: string): Promise<T> {
  if (response.status === 401) {
    // ponytail: a hard redirect (not React state) so a 401 from a background
    // poll reliably lands on /login even though nothing else here is reactive.
    clearToken()
    window.location.assign('/login')
  }
  if (!response.ok) {
    throw new Error(`${path} failed: ${response.status}`)
  }
  return response.json()
}

async function get<T>(path: string): Promise<T> {
  const response = await requestWithAuth(path, {})
  return handleResponse<T>(response, path)
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await requestWithAuth(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return handleResponse<T>(response, path)
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const response = await requestWithAuth(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return handleResponse<T>(response, path)
}

async function del(path: string): Promise<void> {
  const response = await requestWithAuth(path, { method: 'DELETE' })
  if (response.status === 401) {
    clearToken()
    window.location.assign('/login')
  }
  if (!response.ok && response.status !== 204) {
    throw new Error(`${path} failed: ${response.status}`)
  }
}

export function fetchMapCameras(): Promise<{ data: MapCamera[] }> {
  return get('/map/cameras')
}

export function fetchMapActivity(): Promise<{ data: MapActivity[] }> {
  return get('/map/activity')
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await post<LoginResponse>('/auth/login', { username, password })
  setToken(response.access_token)
  setRefreshToken(response.refresh_token)
  return response
}

export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken()
  if (refreshToken) {
    // Best-effort: an operator who's about to lose their tokens either way
    // shouldn't be blocked on the network round trip to revoke server-side.
    fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {})
  }
  clearToken()
}

export function fetchCameras(): Promise<{ data: Camera[] }> {
  return get('/cameras')
}

export function createCamera(body: {
  name: string
  lat: number
  lon: number
  stream_url: string
}): Promise<Camera> {
  return post('/cameras', body)
}

export function updateCamera(id: string, body: Partial<Pick<Camera, 'name' | 'lat' | 'lon' | 'stream_url'>>): Promise<Camera> {
  return patch(`/cameras/${id}`, body)
}

export function deleteCamera(id: string): Promise<void> {
  return del(`/cameras/${id}`)
}

export function startCameraStream(id: string): Promise<Camera> {
  return post(`/cameras/${id}/stream/start`, {})
}

export function stopCameraStream(id: string): Promise<Camera> {
  return post(`/cameras/${id}/stream/stop`, {})
}

export function fetchIdentities(): Promise<{ data: Identity[] }> {
  return get('/identities')
}

export function fetchIdentitySightings(id: string): Promise<{ data: Sighting[] }> {
  return get(`/identities/${id}/sightings`)
}

export function mergeIdentity(id: string, mergeIdentityId: string): Promise<Identity> {
  return post(`/identities/${id}/merge`, { merge_identity_id: mergeIdentityId })
}

export function splitIdentity(id: string, trackId: string): Promise<Identity> {
  return post(`/identities/${id}/split`, { track_id: trackId })
}

export function deleteIdentity(id: string): Promise<void> {
  return del(`/identities/${id}`)
}

export function fetchAuditLog(): Promise<{ data: AuditLogEntry[] }> {
  return get('/audit-log')
}

export function subscribeToSightings(onSighting: (event: SightingEvent) => void): () => void {
  const token = getToken()
  if (!token) return () => {}
  const source = new EventSource(`${API_BASE_URL}/events/stream?token=${encodeURIComponent(token)}`)
  source.onmessage = (message) => {
    try {
      onSighting(JSON.parse(message.data))
    } catch {
      // ponytail: a malformed event just gets dropped, not worth surfacing to the operator.
    }
  }
  return () => source.close()
}
