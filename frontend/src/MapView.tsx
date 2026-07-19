import { CircleMarker, MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { MapActivity, MapCamera } from './api'

const DEFAULT_CENTER: [number, number] = [12.9716, 77.5946]

export function MapView({ cameras, activity }: { cameras: MapCamera[]; activity: MapActivity[] }) {
  const center = cameras.length > 0 ? ([cameras[0].lat, cameras[0].lon] as [number, number]) : DEFAULT_CENTER

  return (
    <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {cameras.map((camera) => (
        <Marker key={camera.id} position={[camera.lat, camera.lon]}>
          <Popup>
            <strong>{camera.name}</strong>
            <br />
            status: {camera.status}
          </Popup>
        </Marker>
      ))}
      {activity.map((sighting) => (
        <CircleMarker key={sighting.id} center={[sighting.lat, sighting.lon]} radius={6} pathOptions={{ color: '#e0433f' }}>
          <Popup>
            identity {sighting.identity_id}
            <br />
            {new Date(sighting.seen_at).toLocaleString()}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
