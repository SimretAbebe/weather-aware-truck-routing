import { useEffect } from 'react'
import { Circle, CircleMarker, MapContainer, Pane, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import { fmtTime } from '../format'
import { RISKS, RISK_COLOR, RISK_LABEL, type Heatmap, type RouteResult } from '../types'

const HEAT_RADIUS_M = 19000 // ~12 miles
const HEAT_OPACITY = [0.14, 0.3, 0.4, 0.5, 0.55]

function FitBounds({ routes }: { routes: RouteResult[] }) {
    const map = useMap()
    useEffect(() => {
        const pts = routes.flatMap((r) => r.checkpoints.map((c) => [c.lat, c.lon] as [number, number]))
        if (pts.length) map.fitBounds(pts, { padding: [40, 40] })
    }, [routes, map])
    return null
}

interface Props {
    routes: RouteResult[]
    selected: number
    onSelect: (rank: number) => void
    heatmap: Heatmap | null
    hour: number
    showHeat: boolean
}

export default function MapView({ routes, selected, onSelect, heatmap, hour, showHeat }: Props) {
    // draw the selected route last so it sits on top
    const drawOrder = [...routes].sort((a, b) => Number(a.rank === selected) - Number(b.rank === selected))
    const active = routes.find((r) => r.rank === selected)

    return (
        <MapContainer center={[39.5, -98.35]} zoom={4} preferCanvas className="map">
            <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <FitBounds routes={routes} />

            {showHeat && heatmap && (
                <Pane name="heat" style={{ zIndex: 350 }}>
                    {heatmap.points.map((p) => {
                        const lvl = p.levels[Math.min(hour, p.levels.length - 1)]
                        return (
                            <Circle key={`${p.lat},${p.lon}`} center={[p.lat, p.lon]} radius={HEAT_RADIUS_M} interactive={false}
                                pathOptions={{ stroke: false, fillColor: RISK_COLOR[RISKS[lvl]], fillOpacity: HEAT_OPACITY[lvl] }} />
                        )
                    })}
                </Pane>
            )}

            {drawOrder.flatMap((r) =>
                r.checkpoints.map((c) => (
                    <Polyline key={`${r.rank}-${c.index}`} positions={c.path}
                        eventHandlers={{ click: () => onSelect(r.rank) }}
                        pathOptions={{ color: RISK_COLOR[c.risk], weight: r.rank === selected ? 6 : 3, opacity: r.rank === selected ? 0.95 : 0.45 }} />
                )),
            )}

            {active?.checkpoints.map((c, i, all) => {
                const end = i === 0 || i === all.length - 1
                return (
                    <CircleMarker key={c.index} center={[c.lat, c.lon]} radius={end ? 8 : 5}
                        pathOptions={{ color: '#fff', weight: 2, fillColor: RISK_COLOR[c.risk], fillOpacity: 1 }}>
                        <Popup>
                            <strong>{i === 0 ? 'Start' : i === all.length - 1 ? 'Destination' : `Mile ${c.mile}`}</strong><br />
                            ETA {fmtTime(c.eta)}<br />
                            Risk: {RISK_LABEL[c.risk]}{c.load_override ? ' (load rule)' : ''}<br />
                            Wind {c.wind_mph} mph (gusts {c.gust_mph})<br />
                            Rain {c.rain_in_hr} in/hr · Snow {c.snow_in_hr} in/hr
                        </Popup>
                    </CircleMarker>
                )
            })}
        </MapContainer>
    )
}