import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { deleteCamera, fetchMapCameras, login, subscribeToSightings } from './api'
import { clearToken, getRefreshToken, getToken, setRefreshToken, setToken } from './auth'

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

  it('stores the access and refresh tokens returned by a successful login', async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(200, { access_token: 'new-token', refresh_token: 'new-refresh-token', token_type: 'bearer' })
    )

    await login('operator1', 'correct-password')

    expect(getToken()).toBe('new-token')
    expect(getRefreshToken()).toBe('new-refresh-token')
  })

  it('clears the token and redirects to /login on a 401 with no refresh token stored', async () => {
    setToken('stale-token')
    vi.mocked(fetch).mockResolvedValue(jsonResponse(401, { error: { code: 'unauthorized', message: 'nope' } }))

    await expect(fetchMapCameras()).rejects.toThrow()

    expect(getToken()).toBeNull()
    expect(location.assign).toHaveBeenCalledWith('/login')
  })

  it('refreshes the access token and retries once after a 401, when a refresh token is stored', async () => {
    setToken('stale-token')
    setRefreshToken('refresh-token-abc')
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(401, { error: { code: 'unauthorized', message: 'expired' } }))
      .mockResolvedValueOnce(
        jsonResponse(200, { access_token: 'fresh-token', refresh_token: 'fresh-refresh-token', token_type: 'bearer' })
      )
      .mockResolvedValueOnce(jsonResponse(200, { data: ['ok'] }))

    const result = await fetchMapCameras()

    expect(result).toEqual({ data: ['ok'] })
    expect(getToken()).toBe('fresh-token')
    expect(getRefreshToken()).toBe('fresh-refresh-token')
    expect(location.assign).not.toHaveBeenCalled()

    const [refreshUrl] = vi.mocked(fetch).mock.calls[1]
    expect(refreshUrl).toContain('/auth/refresh')
    const [, retryInit] = vi.mocked(fetch).mock.calls[2]
    const retryHeaders = (retryInit?.headers ?? {}) as Record<string, string>
    expect(retryHeaders.Authorization).toBe('Bearer fresh-token')
  })

  it('clears tokens and redirects to /login when the refresh attempt itself fails', async () => {
    setToken('stale-token')
    setRefreshToken('bad-refresh-token')
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(401, { error: { code: 'unauthorized', message: 'expired' } }))
      .mockResolvedValueOnce(jsonResponse(401, { error: { code: 'unauthorized', message: 'invalid refresh token' } }))

    await expect(fetchMapCameras()).rejects.toThrow()

    expect(getToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
    expect(location.assign).toHaveBeenCalledWith('/login')
  })

  it('sends an authenticated DELETE and tolerates a 204 with no body', async () => {
    setToken('token-123')
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }))

    await deleteCamera('cam_1')

    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(url).toContain('/cameras/cam_1')
    expect(init?.method).toBe('DELETE')
    const headers = (init?.headers ?? {}) as Record<string, string>
    expect(headers.Authorization).toBe('Bearer token-123')
  })

  it('clears the token and redirects to /login when a DELETE 401s', async () => {
    setToken('stale-token')
    vi.mocked(fetch).mockResolvedValue(jsonResponse(401, { error: { code: 'unauthorized', message: 'nope' } }))

    await expect(deleteCamera('cam_1')).rejects.toThrow()

    expect(getToken()).toBeNull()
    expect(location.assign).toHaveBeenCalledWith('/login')
  })
})

describe('subscribeToSightings', () => {
  class FakeEventSource {
    static instances: FakeEventSource[] = []
    url: string
    onmessage: ((event: { data: string }) => void) | null = null
    closed = false
    constructor(url: string) {
      this.url = url
      FakeEventSource.instances.push(this)
    }
    close() {
      this.closed = true
    }
  }

  beforeEach(() => {
    clearToken()
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('does nothing without a stored token', () => {
    const unsubscribe = subscribeToSightings(() => {})
    expect(FakeEventSource.instances).toHaveLength(0)
    unsubscribe()
  })

  it('opens an EventSource carrying the token and forwards parsed messages', () => {
    setToken('token-123')
    const received: unknown[] = []

    const unsubscribe = subscribeToSightings((event) => received.push(event))

    expect(FakeEventSource.instances).toHaveLength(1)
    const source = FakeEventSource.instances[0]
    expect(source.url).toContain('token=token-123')

    if (!source.onmessage) throw new Error('expected onmessage to be set')
    source.onmessage({ data: JSON.stringify({ identity_id: 'idn_1' }) })
    expect(received).toEqual([{ identity_id: 'idn_1' }])

    unsubscribe()
    expect(source.closed).toBe(true)
  })
})
