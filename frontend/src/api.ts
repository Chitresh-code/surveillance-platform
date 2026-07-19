import { clearToken, getToken, setToken } from './auth'

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
  token_type: string
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
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
  const response = await fetch(`${API_BASE_URL}${path}`, { headers: authHeaders() })
  return handleResponse<T>(response, path)
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  })
  return handleResponse<T>(response, path)
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
  return response
}
