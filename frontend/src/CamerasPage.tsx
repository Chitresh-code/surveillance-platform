import { useEffect, useState, type FormEvent } from 'react'
import {
  createCamera,
  deleteCamera,
  fetchCameras,
  startCameraStream,
  stopCameraStream,
  type Camera,
} from './api'

const EMPTY_FORM = { name: '', lat: '', lon: '', stream_url: '' }

export function CamerasPage() {
  const [cameras, setCameras] = useState<Camera[]>([])
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)

  async function load() {
    try {
      const res = await fetchCameras()
      setCameras(res.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cameras')
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    try {
      await createCamera({ name: form.name, lat: Number(form.lat), lon: Number(form.lon), stream_url: form.stream_url })
      setForm(EMPTY_FORM)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to register camera')
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteCamera(id)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete camera (it may still have recorded tracks)')
    }
  }

  async function handleToggleStream(camera: Camera) {
    try {
      if (camera.status === 'streaming') {
        await stopCameraStream(camera.id)
      } else {
        await startCameraStream(camera.id)
      }
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle stream')
    }
  }

  return (
    <div className="page">
      <h1 className="page-title">[ Cameras ]</h1>
      {error && <div className="page-error">{error}</div>}

      <section className="panel">
        <div className="panel-title">Register camera</div>
        <form className="inline-form" onSubmit={handleCreate}>
          <input placeholder="name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          <input placeholder="lat" value={form.lat} onChange={(event) => setForm({ ...form, lat: event.target.value })} required />
          <input placeholder="lon" value={form.lon} onChange={(event) => setForm({ ...form, lon: event.target.value })} required />
          <input
            placeholder="stream_url"
            value={form.stream_url}
            onChange={(event) => setForm({ ...form, stream_url: event.target.value })}
            required
          />
          <button type="submit">Add</button>
        </form>
      </section>

      <table className="table">
        <thead>
          <tr>
            <th>id</th>
            <th>name</th>
            <th>status</th>
            <th>lat</th>
            <th>lon</th>
            <th>stream_url</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {cameras.map((camera) => (
            <tr key={camera.id}>
              <td>{camera.id}</td>
              <td>{camera.name}</td>
              <td>
                <span className={`status-dot ${camera.status === 'streaming' ? 'live' : 'idle'}`} />
                {camera.status}
              </td>
              <td>{camera.lat}</td>
              <td>{camera.lon}</td>
              <td className="truncate">{camera.stream_url}</td>
              <td className="row-actions">
                <button type="button" onClick={() => handleToggleStream(camera)}>
                  {camera.status === 'streaming' ? 'Stop' : 'Start'}
                </button>
                <button type="button" className="danger" onClick={() => handleDelete(camera.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
