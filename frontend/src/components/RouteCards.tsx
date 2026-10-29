import { fmtHours } from '../format'
import { RISKS, RISK_COLOR, RISK_LABEL, type RouteResult } from '../types'

interface Props { routes: RouteResult[]; selected: number; onSelect: (rank: number) => void }

export default function RouteCards({ routes, selected, onSelect }: Props) {
    return (
        <div className="cards">
            {routes.map((r) => {
                const m = r.miles_by_level
                const total = RISKS.reduce((s, k) => s + m[k], 0) || 1
                return (
                    <button key={r.rank} className={`card ${r.rank === selected ? 'sel' : ''}`} onClick={() => onSelect(r.rank)}>
                        <div className="card-head">
                            <strong>Route {r.rank}</strong>
                            {r.recommended && <span className="badge">Recommended</span>}
                            <span className="muted">{r.distance_mi} mi · {fmtHours(r.duration_h)}</span>
                        </div>
                        <div className="bar">
                            {RISKS.map((k) => m[k] > 0 && (
                                <span key={k} title={`${RISK_LABEL[k]}: ${m[k]} mi`}
                                    style={{ width: `${(m[k] / total) * 100}%`, background: RISK_COLOR[k] }} />
                            ))}
                        </div>
                        <div className="stats">
                            <span>No Travel {m.no_travel} mi</span><span>Severe {m.severe} mi</span>
                            <span>High {m.high} mi</span><span>Avg risk {r.avg_risk}/4</span>
                        </div>
                        <p className="reason">{r.reason}</p>
                        {r.beyond_forecast && <p className="warn">Part of this trip is past the forecast window; the last available hour was used.</p>}
                    </button>
                )
            })}
        </div>
    )
}