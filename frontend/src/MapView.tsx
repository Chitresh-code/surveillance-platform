import L from 'leaflet'
import { CircleMarker, MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { MapActivity, MapCamera } from './api'

const DEFAULT_CENTER: [number, number] = [12.9716, 77.5946]

// ponytail: Leaflet's default marker icon is a bundled PNG whose relative URL
// doesn't resolve under Vite, rendering as a broken image. A CSS-only reticle
// sidesteps the asset-resolution problem entirely and fits the terminal theme
// better than the stock blue pin would have anyway.
const cameraIcon = L.divIcon({
  className: 'camera-marker',
  html: '<span></span>',
  iconSize: [16, 16],
})

export function MapView({ cameras, activity }: { cameras: MapCamera[]; activity: MapActivity[] }) {
  const center = cameras.length > 0 ? ([cameras[0].lat, cameras[0].lon] as [number, number]) : DEFAULT_CENTER

  return (
    <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      {cameras.map((camera) => (
        <Marker key={camera.id} position={[camera.lat, camera.lon]} icon={cameraIcon}>
          <Popup>
            <strong>{camera.name}</strong>
            <br />
            status: {camera.status}
          </Popup>
        </Marker>
      ))}
      {activity.map((sighting) => (
        <CircleMarker key={sighting.id} center={[sighting.lat, sighting.lon]} radius={6} pathOptions={{ color: '#ffb400' }}>
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
