import { useEffect, useState } from 'react'
import { geocode } from '../api'
import type { Place } from '../types'

interface Props { label: string; value: Place | null; onChange: (p: Place | null) => void }

export default function PlaceInput({ label, value, onChange }: Props) {
    const [text, setText] = useState('')
    const [options, setOptions] = useState<Place[]>([])
    const [open, setOpen] = useState(false)

    useEffect(() => {
        if (value || text.trim().length < 3) return
        const ctl = new AbortController()
        const t = setTimeout(() => {
            geocode(text.trim(), ctl.signal).then((r) => { setOptions(r); setOpen(true) }).catch(() => { })
        }, 300)
        return () => { clearTimeout(t); ctl.abort() }
    }, [text, value])

    const shown = value ? [] : options

    return (
        <div className="field">
            <span>{label}</span>
            <input
                aria-label={label}
                className={value ? 'ok' : ''}
                value={text}
                placeholder="City or address"
                onChange={(e) => { setText(e.target.value); onChange(null) }}
                onFocus={() => setOpen(true)}
                onBlur={() => setTimeout(() => setOpen(false), 150)}
            />
            {open && shown.length > 0 && (
                <ul className="suggest">
                    {shown.map((p) => (
                        <li key={`${p.lat},${p.lon}`} onMouseDown={() => { setText(p.label); onChange(p); setOpen(false) }}>
                            {p.label}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}