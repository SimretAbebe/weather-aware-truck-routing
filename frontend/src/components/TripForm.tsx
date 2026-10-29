import { useState } from 'react'
import PlaceInput from './PlaceInput'
import type { AnalyzeRequest, Place } from '../types'

interface Props { busy: boolean; onSubmit: (req: AnalyzeRequest) => Promise<void> }

export default function TripForm({ busy, onSubmit }: Props) {
    const [origin, setOrigin] = useState<Place | null>(null)
    const [destination, setDestination] = useState<Place | null>(null)
    const [departure, setDeparture] = useState(() => {
        const d = new Date()
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
        return d.toISOString().slice(0, 16)
    })
    const [loadLb, setLoadLb] = useState(40000)
    const [interval, setInterval] = useState<10 | 25 | 50>(25)

    const ready = origin && destination && !busy

    function submit(e: React.FormEvent) {
        e.preventDefault()
        if (!origin || !destination) return
        onSubmit({
            origin: { lat: origin.lat, lon: origin.lon },
            destination: { lat: destination.lat, lon: destination.lon },
            departure,
            load_lb: loadLb,
            interval_mi: interval,
        })
    }

    return (
        <form className="form" onSubmit={submit}>
            <PlaceInput label="Origin" value={origin} onChange={setOrigin} />
            <PlaceInput label="Destination" value={destination} onChange={setDestination} />
            <div className="row">
                <div className="field">
                    <span>Departure</span>
                    <input type="datetime-local" value={departure}
                        onChange={(e) => setDeparture(e.target.value)} />
                </div>
                <div className="field">
                    <span>Load (lb)</span>
                    <input type="number" min={0} max={80000} step={1000} value={loadLb}
                        onChange={(e) => setLoadLb(Number(e.target.value))} />
                </div>
            </div>
            <div className="row">
                <div className="field">
                    <span>Checkpoint interval</span>
                    <select value={interval} onChange={(e) => setInterval(Number(e.target.value) as 10 | 25 | 50)}>
                        <option value={10}>Every 10 mi</option>
                        <option value={25}>Every 25 mi</option>
                        <option value={50}>Every 50 mi</option>
                    </select>
                </div>
            </div>
            <button type="submit" className="primary" disabled={!ready}>
                {busy ? 'Analyzing…' : 'Analyze Route'}
            </button>
        </form>
    )
}
