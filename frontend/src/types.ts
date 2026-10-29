export type Risk = 'low' | 'moderate' | 'high' | 'severe' | 'no_travel'
export const RISKS: Risk[] = ['low', 'moderate', 'high', 'severe', 'no_travel']
export const RISK_COLOR: Record<Risk, string> = {
    low: '#2e9e5b', moderate: '#e6c229', high: '#f08a24', severe: '#d7263d', no_travel: '#1b1b1f',
}
export const RISK_LABEL: Record<Risk, string> = {
    low: 'Low', moderate: 'Moderate', high: 'High', severe: 'Severe', no_travel: 'No Travel',
}

export interface Place { label: string; lat: number; lon: number }

export interface AnalyzeRequest {
    origin: { lat: number; lon: number }
    destination: { lat: number; lon: number }
    departure: string
    load_lb: number
    interval_mi: 10 | 25 | 50
}

export interface CheckpointResult {
    index: number; mile: number; lat: number; lon: number; eta: string
    risk: Risk; load_override: boolean
    wind_mph: number; gust_mph: number; rain_in_hr: number; snow_in_hr: number
    path: [number, number][]
}

export interface RouteResult {
    rank: number; recommended: boolean; reason: string
    distance_mi: number; duration_h: number; avg_risk: number
    miles_by_level: Record<Risk, number>
    beyond_forecast: boolean
    checkpoints: CheckpointResult[]
}

export interface Heatmap {
    start: string; hours: number
    points: { lat: number; lon: number; levels: number[] }[]
}

export interface AnalyzeResponse { routes: RouteResult[]; heatmap: Heatmap | null }