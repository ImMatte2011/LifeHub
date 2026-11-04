import { useEffect, useRef } from 'react'
import type { Map as LeafletMap } from 'leaflet'

type Place = { id: string; name: string; description?: string | null; latitude?: number | null; longitude?: number | null }

export default function MapView({ places, enabled }: { places: Record<string, unknown>[]; enabled: boolean }) {
  const node = useRef<HTMLDivElement>(null)
  const map = useRef<LeafletMap | null>(null)
  const markerLayer = useRef<import('leaflet').LayerGroup | null>(null)

  useEffect(() => {
    if (!enabled || !node.current || map.current) return
    let disposed = false
    void import('leaflet').then((L) => {
      if (disposed || !node.current) return
      map.current = L.map(node.current).setView([41.9, 12.5], 5)
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors', maxZoom: 19 }).addTo(map.current)
      markerLayer.current = L.layerGroup().addTo(map.current)
    })
    return () => { disposed = true; map.current?.remove(); map.current = null }
  }, [enabled])

  useEffect(() => {
    if (!map.current || !markerLayer.current) return
    void import('leaflet').then((L) => {
      const layer = markerLayer.current
      if (!layer) return
      layer.clearLayers()
      places.forEach((raw) => {
        const place = raw as unknown as Place
        if (typeof place.latitude === 'number' && typeof place.longitude === 'number') {
          L.marker([place.latitude, place.longitude]).bindPopup(`<strong>${escapeHtml(place.name)}</strong>${place.description ? `<br>${escapeHtml(place.description)}` : ''}`).addTo(layer)
        }
      })
    })
  }, [places])

  if (!enabled) return <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 text-sm text-zinc-400">Map services are turned off. Places can still be stored and browsed without coordinates.</div>
  return <div className="relative overflow-hidden rounded-xl border border-zinc-800"><div ref={node} className="h-72 w-full bg-zinc-900 sm:h-96" /><button type="button" onClick={() => {
    if (!navigator.geolocation) return
    navigator.geolocation.getCurrentPosition((position) => {
      void import('leaflet').then((L) => {
        const point: [number, number] = [position.coords.latitude, position.coords.longitude]
        map.current?.setView(point, 14)
        L.circleMarker(point, { radius: 8, color: '#818cf8', fillColor: '#6366f1', fillOpacity: 0.8 }).bindPopup('Your location').addTo(map.current!)
      })
    })
  }} className="absolute right-3 top-3 z-[500] rounded-lg border border-zinc-700 bg-zinc-950/90 px-3 py-2 text-xs text-zinc-100 shadow">My location</button></div>
}

function escapeHtml(value: string) { return value.replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]!) }
