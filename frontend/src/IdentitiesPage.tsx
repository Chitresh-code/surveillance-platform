import { useEffect, useState } from 'react'
import {
  deleteIdentity,
  fetchIdentities,
  fetchIdentitySightings,
  mergeIdentity,
  splitIdentity,
  type Identity,
  type Sighting,
} from './api'

export function IdentitiesPage() {
  const [identities, setIdentities] = useState<Identity[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [sightings, setSightings] = useState<Sighting[]>([])
  const [error, setError] = useState<string | null>(null)
  const [mergeTarget, setMergeTarget] = useState('')
  const [splitTrackId, setSplitTrackId] = useState('')

  async function load() {
    try {
      const res = await fetchIdentities()
      setIdentities(res.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load identities')
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function select(id: string) {
    setSelected(id)
    try {
      const res = await fetchIdentitySightings(id)
      setSightings(res.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sightings')
    }
  }

  async function handleMerge() {
    if (!selected || !mergeTarget) return
    try {
      await mergeIdentity(selected, mergeTarget)
      setMergeTarget('')
      await load()
      await select(selected)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Merge failed')
    }
  }

  async function handleSplit() {
    if (!selected || !splitTrackId) return
    try {
      const result = await splitIdentity(selected, splitTrackId)
      setSplitTrackId('')
      await load()
      await select(result.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Split failed')
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteIdentity(id)
      if (selected === id) {
        setSelected(null)
        setSightings([])
      }
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  return (
    <div className="page">
      <h1 className="page-title">[ Identities ]</h1>
      {error && <div className="page-error">{error}</div>}

      <div className="split-layout">
        <table className="table">
          <thead>
            <tr>
              <th>id</th>
              <th>first_seen</th>
              <th>last_seen</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {identities.map((identity) => (
              <tr key={identity.id} className={identity.id === selected ? 'selected' : ''}>
                <td>
                  <button type="button" className="link" onClick={() => select(identity.id)}>
                    {identity.id}
                  </button>
                </td>
                <td>{new Date(identity.first_seen).toLocaleString()}</td>
                <td>{new Date(identity.last_seen).toLocaleString()}</td>
                <td>
                  <button type="button" className="danger" onClick={() => handleDelete(identity.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {selected && (
          <section className="panel">
            <div className="panel-title">{selected} :: sightings</div>
            <table className="table">
              <thead>
                <tr>
                  <th>camera</th>
                  <th>track</th>
                  <th>seen_at</th>
                  <th>confidence</th>
                </tr>
              </thead>
              <tbody>
                {sightings.map((sighting) => (
                  <tr key={sighting.id}>
                    <td>{sighting.camera_id}</td>
                    <td>{sighting.track_id}</td>
                    <td>{new Date(sighting.seen_at).toLocaleString()}</td>
                    <td>{sighting.match_confidence.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="inline-form">
              <input
                placeholder="merge_identity_id"
                value={mergeTarget}
                onChange={(event) => setMergeTarget(event.target.value)}
              />
              <button type="button" onClick={handleMerge}>
                Merge
              </button>
            </div>
            <div className="inline-form">
              <input
                placeholder="track_id to split off"
                value={splitTrackId}
                onChange={(event) => setSplitTrackId(event.target.value)}
              />
              <button type="button" onClick={handleSplit}>
                Split
              </button>
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
