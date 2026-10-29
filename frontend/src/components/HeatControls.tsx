import { RISKS, RISK_COLOR, RISK_LABEL, type Heatmap } from '../types'

interface Props {
    heatmap: Heatmap
    hour: number
    setHour: (h: number) => void
    show: boolean
    setShow: (s: boolean) => void
}

export default function HeatControls({ heatmap, hour, setHour, show, setShow }: Props) {
    const when = new Date(new Date(heatmap.start).getTime() + hour * 3600e3)
    return (
        <div className="heatbar">
            <label className="check">
                <input type="checkbox" checked={show} onChange={(e) => setShow(e.target.checked)} /> Weather heatmap
            </label>
            <input type="range" min={0} max={heatmap.hours - 1} value={hour} disabled={!show}
                onChange={(e) => setHour(Number(e.target.value))} aria-label="Forecast hour" />
            <span className="when">
                +{hour}h · {when.toLocaleString([], { weekday: 'short', hour: 'numeric', minute: '2-digit' })}
            </span>
            <span className="legend">
                {RISKS.map((k) => (<i key={k}><b style={{ background: RISK_COLOR[k] }} />{RISK_LABEL[k]}</i>))}
            </span>
        </div>
    )
}