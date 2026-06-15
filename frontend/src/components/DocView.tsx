import { useState, useEffect } from "react"
import type { Event } from "../types"
import * as api from "../api"
import EventCard from "./EventCard"

interface Props {
  artifactId: string
  libraryId: string
}

// TODO: Add edit UI here. The createEdit API function is available (api.createEdit),
// but the edit flow involves batch confirm (scope: surface/substance) which is complex.
// Defer full edit UI to a later iteration.

export default function DocView({ artifactId, libraryId }: Props) {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Lens feed state
  const [lensIngesting, setLensIngesting] = useState(false)
  const [lensMessage, setLensMessage] = useState<string | null>(null)
  const [lensError, setLensError] = useState<string | null>(null)
  const [lensFeedCount, setLensFeedCount] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    api
      .getDoc(artifactId)
      .then(({ events: fetched }) => {
        if (!cancelled) {
          setEvents(fetched)
          setLoading(false)
        }
      })
      .catch(e => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load doc")
          setLoading(false)
        }
      })

    return () => { cancelled = true }
  }, [artifactId])

  // Check existing lens feed entries on mount
  useEffect(() => {
    let cancelled = false

    api
      .queryLensFeed(libraryId)
      .then(({ entries }) => {
        if (!cancelled) {
          setLensFeedCount(entries.length)
        }
      })
      .catch(() => {
        // Non-critical — just leave count as null
      })

    return () => { cancelled = true }
  }, [libraryId])

  const handleIngestLens = async () => {
    setLensIngesting(true)
    setLensMessage(null)
    setLensError(null)
    try {
      const { entries } = await api.ingestLensFeed(artifactId, libraryId)
      setLensMessage(`写入成功: ${entries.length} 条 Lens 条目`)
      setLensFeedCount(prev => (prev ?? 0) + entries.length)
    } catch (e) {
      setLensError(e instanceof Error ? e.message : "写入 Lens 失败")
    } finally {
      setLensIngesting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-zinc-500">Loading doc...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-red-400">{error}</p>
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-zinc-500">No doc events yet.</p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
      {/* Lens feed controls */}
      <div className="flex items-center gap-3">
        <button
          className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handleIngestLens}
          disabled={lensIngesting}
        >
          {lensIngesting ? "写入中..." : "写入 Lens"}
        </button>
        {lensMessage && (
          <span className="text-sm text-emerald-400">{lensMessage}</span>
        )}
        {lensError && (
          <span className="text-sm text-red-400">{lensError}</span>
        )}
      </div>

      {/* Doc events */}
      <div className="space-y-3">
        {events.map(event => (
          <EventCard key={event.id} event={event} />
        ))}
      </div>

      {/* Lens Feed status section */}
      <div className="border-t border-zinc-800 pt-3 mt-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-2">
          Lens Feed
        </p>
        {lensFeedCount !== null && lensFeedCount > 0 ? (
          <p className="text-sm text-zinc-400">
            已写入 {lensFeedCount} 条 Lens 条目
          </p>
        ) : (
          <p className="text-sm text-zinc-600">尚未写入 Lens</p>
        )}
      </div>
    </div>
  )
}
