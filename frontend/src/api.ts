import type { AnalyzeRequest, AnalyzeResponse, Place } from './types'

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://127.0.0.1:8000'

async function errorMessage(r: Response): Promise<string> {
    try {
        const j = await r.json()
        if (j.detail) return String(j.detail)
        return Object.entries(j)
            .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : JSON.stringify(v)}`)
            .join(' | ')
    } catch {
        return `Request failed (${r.status})`
    }
}

export async function analyze(body: AnalyzeRequest): Promise<AnalyzeResponse> {
    const r = await fetch(`${BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
    if (!r.ok) throw new Error(await errorMessage(r))
    return r.json()
}

export async function geocode(q: string, signal: AbortSignal): Promise<Place[]> {
    const r = await fetch(`${BASE}/api/geocode?q=${encodeURIComponent(q)}`, { signal })
    if (!r.ok) return []
    return (await r.json()).results
}