/** Format a decimal-hours value like 5.25 → "5h 15m" */
export function fmtHours(h: number): string {
    const hrs = Math.floor(h)
    const mins = Math.round((h - hrs) * 60)
    if (hrs === 0) return `${mins}m`
    if (mins === 0) return `${hrs}h`
    return `${hrs}h ${mins}m`
}

/** Format an ISO timestamp to a short local time string */
export function fmtTime(iso: string): string {
    return new Date(iso).toLocaleString([], {
        weekday: 'short',
        hour: 'numeric',
        minute: '2-digit',
    })
}
