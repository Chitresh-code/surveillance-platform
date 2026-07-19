import { useEffect, useState } from 'react'
import { fetchAuditLog, type AuditLogEntry } from './api'

export function AuditLogPage() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAuditLog()
      .then((res) => setEntries(res.data))
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load audit log'))
  }, [])

  return (
    <div className="page">
      <h1 className="page-title">[ Audit log ]</h1>
      {error && <div className="page-error">{error}</div>}
      <table className="table">
        <thead>
          <tr>
            <th>time</th>
            <th>operator</th>
            <th>action</th>
            <th>resource</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id}>
              <td>{new Date(entry.created_at).toLocaleString()}</td>
              <td>{entry.operator_id}</td>
              <td>{entry.action}</td>
              <td>
                {entry.resource_type}:{entry.resource_id}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
