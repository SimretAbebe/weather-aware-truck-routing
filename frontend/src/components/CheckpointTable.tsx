import { fmtTime } from '../format'
import { RISK_COLOR, RISK_LABEL, type RouteResult } from '../types'

interface Props { route: RouteResult }

export default function CheckpointTable({ route }: Props) {
    return (
        <>
            <h3>Checkpoints — Route {route.rank}</h3>
            <div className="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Mile</th>
                            <th>ETA</th>
                            <th>Risk</th>
                            <th>Wind</th>
                            <th>Gust</th>
                            <th>Rain</th>
                            <th>Snow</th>
                        </tr>
                    </thead>
                    <tbody>
                        {route.checkpoints.map((c) => (
                            <tr key={c.index}>
                                <td>{c.mile}</td>
                                <td>{fmtTime(c.eta)}</td>
                                <td>
                                    <span className="pill" style={{ background: RISK_COLOR[c.risk] }}>
                                        {RISK_LABEL[c.risk]}{c.load_override ? ' ⚠' : ''}
                                    </span>
                                </td>
                                <td>{c.wind_mph} mph</td>
                                <td>{c.gust_mph} mph</td>
                                <td>{c.rain_in_hr} in/hr</td>
                                <td>{c.snow_in_hr} in/hr</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </>
    )
}
