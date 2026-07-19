import type { ReactElement } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AuditLogPage } from './AuditLogPage'
import { getToken } from './auth'
import { CamerasPage } from './CamerasPage'
import { IdentitiesPage } from './IdentitiesPage'
import { Login } from './Login'
import { MapPage } from './MapPage'
import { Shell } from './Shell'

function RequireAuth({ children }: { children: ReactElement }) {
  return getToken() ? <Shell>{children}</Shell> : <Navigate to="/login" replace />
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <MapPage />
          </RequireAuth>
        }
      />
      <Route
        path="/cameras"
        element={
          <RequireAuth>
            <CamerasPage />
          </RequireAuth>
        }
      />
      <Route
        path="/identities"
        element={
          <RequireAuth>
            <IdentitiesPage />
          </RequireAuth>
        }
      />
      <Route
        path="/audit-log"
        element={
          <RequireAuth>
            <AuditLogPage />
          </RequireAuth>
        }
      />
    </Routes>
  )
}

export default App
