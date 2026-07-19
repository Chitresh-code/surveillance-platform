import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchMapCameras, login } from './api'
import { clearToken, getToken, setToken } from './auth'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('api.ts auth behavior', () => {
  beforeEach(() => {
    clearToken()
    vi.stubGlobal('fetch', vi.fn())
    vi.stubGlobal('location', { assign: vi.fn() })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('attaches an Authorization header when a token is stored', async () => {
    setToken('token-123')
    vi.mocked(fetch).mockResolvedValue(jsonResponse(200, { data: [] }))

    await fetchMapCameras()

    const [, init] = vi.mocked(fetch).mock.calls[0]
    const headers = (init?.headers ?? {}) as Record<string, string>
    expect(headers.Authorization).toBe('Bearer token-123')
  })

  it('sends no Authorization header when there is no token', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(200, { data: [] }))

    await fetchMapCameras()

    const [, init] = vi.mocked(fetch).mock.calls[0]
    const headers = (init?.headers ?? {}) as Record<string, string>
    expect(headers.Authorization).toBeUndefined()
  })

  it('stores the token returned by a successful login', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(200, { access_token: 'new-token', token_type: 'bearer' }))

    await login('operator1', 'correct-password')

    expect(getToken()).toBe('new-token')
  })

  it('clears the token and redirects to /login on a 401', async () => {
    setToken('stale-token')
    vi.mocked(fetch).mockResolvedValue(jsonResponse(401, { error: { code: 'unauthorized', message: 'nope' } }))

    await expect(fetchMapCameras()).rejects.toThrow()

    expect(getToken()).toBeNull()
    expect(location.assign).toHaveBeenCalledWith('/login')
  })
})
