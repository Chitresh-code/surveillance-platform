import { useEffect, useRef, useState } from 'react'
import { subscribeToSightings, type SightingEvent } from './api'

const MAX_LINES = 30

export function LiveFeed() {
  const [events, setEvents] = useState<SightingEvent[]>([])
  const linesRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    return subscribeToSightings((event) => {
      setEvents((prev) => [...prev.slice(-(MAX_LINES - 1)), event])
    })
  }, [])

  useEffect(() => {
    linesRef.current?.scrollTo({ top: linesRef.current.scrollHeight })
  }, [events])

  return (
    <div className="panel live-feed">
      <div className="panel-title">
        <span className="status-dot live" /> LIVE FEED
      </div>
      <div className="live-feed-lines" ref={linesRef}>
        {events.length === 0 && <div className="live-feed-empty cursor">&gt; awaiting signal</div>}
        {events.map((event, index) => (
          <div key={`${event.track_id}-${index}`} className="live-feed-line">
            <span className="live-feed-prompt">&gt;&gt;</span> {event.identity_id} @ {event.camera_id}{' '}
            <span className="live-feed-dim">conf={event.match_confidence.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
