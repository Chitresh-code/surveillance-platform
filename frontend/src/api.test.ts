import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { deleteCamera, fetchMapCameras, login, subscribeToSightings } from './api'
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
