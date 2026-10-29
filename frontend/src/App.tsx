import { useDeferredValue, useState } from 'react'
import { analyze } from './api'
import CheckpointTable from './components/CheckpointTable'
import HeatControls from './components/HeatControls'
import MapView from './components/MapView'
import RouteCards from './components/RouteCards'
import TripForm from './components/TripForm'
import type { AnalyzeRequest, AnalyzeResponse } from './types'
import './App.css'

export default function App() {
  const [data, setData] = useState<AnalyzeResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState(1)
  const [hour, setHour] = useState(0)
  const [showHeat, setShowHeat] = useState(true)
  const deferredHour = useDeferredValue(hour) // keeps the slider responsive while circles repaint

  async function run(req: AnalyzeRequest) {
    setBusy(true)
    setError(null)
    try {
      const res = await analyze(req)
      setData(res)
      setSelected(res.routes.find((r) => r.recommended)?.rank ?? 1)
      setHour(0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  const active = data?.routes.find((r) => r.rank === selected)

  return (
    <div className="app">
      <aside>
        <h1>Weather-Aware Truck Routing</h1>
        <TripForm busy={busy} onSubmit={run} />
        {busy && <p className="muted">Fetching routes and forecasts… the first request can take up to a minute while the server wakes up.</p>}
        {error && <p className="error" role="alert">{error}</p>}
        {data && (
          <>
            {data.routes.length < 3 && <p className="muted">Only {data.routes.length} distinct drivable routes exist for this trip.</p>}
            <RouteCards routes={data.routes} selected={selected} onSelect={setSelected} />
            {active && <CheckpointTable route={active} />}
          </>
        )}
      </aside>
      <main>
        <MapView routes={data?.routes ?? []} selected={selected} onSelect={setSelected}
          heatmap={data?.heatmap ?? null} hour={deferredHour} showHeat={showHeat} />
        {data?.heatmap && <HeatControls heatmap={data.heatmap} hour={hour} setHour={setHour} show={showHeat} setShow={setShowHeat} />}
        {data && !data.heatmap && <p className="warn bar-msg">Heatmap unavailable for this trip.</p>}
      </main>
    </div>
  )
}