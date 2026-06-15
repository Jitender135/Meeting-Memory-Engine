import { useEffect, useState } from "react"
import { getHealth, getMeetings, postIngest, postTranscribe } from "../lib/api"

export default function Sidebar() {
  const [health, setHealth] = useState(null)
  const [meetings, setMeetings] = useState([])
  const [loading, setLoading] = useState(false)

  const [audioFile, setAudioFile] = useState(null)
  const [meetingTitle, setMeetingTitle] = useState("Recorded Meeting")
  const [meetingDate, setMeetingDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [transcribing, setTranscribing] = useState(false)
  const [transcribeResult, setTranscribeResult] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      const h = await getHealth()
      if (cancelled) return
      setHealth(h)
      if (h.status === "ok" && h.pipeline === "ready") {
        const m = await getMeetings()
        if (cancelled) return
        setMeetings(m.meetings || [])
      }
    }

    load()
    return () => { cancelled = true }
  }, [])

  async function loadData() {
    const h = await getHealth()
    setHealth(h)
    if (h.status === "ok" && h.pipeline === "ready") {
      const m = await getMeetings()
      setMeetings(m.meetings || [])
    }
  }

  async function handleReindex() {
    setLoading(true)
    await postIngest()
    await loadData()
    setLoading(false)
  }

  async function handleTranscribe() {
    if (!audioFile) return
    setTranscribing(true)
    setTranscribeResult(null)

    const res = await postTranscribe(audioFile, meetingTitle, meetingDate)
    setTranscribeResult(res)

    if (res.status === "success") {
      await loadData()
      setAudioFile(null)
    }

    setTranscribing(false)
  }

  const statusColor =
    health?.status === "ok" && health?.pipeline === "ready"
      ? "bg-green-500"
      : health?.status === "ok"
      ? "bg-yellow-500"
      : "bg-red-500"

  const statusText =
    health?.status === "ok" && health?.pipeline === "ready"
      ? "Pipeline ready"
      : health?.status === "ok"
      ? "Not ingested"
      : "API unreachable"

  return (
    <aside className="w-72 shrink-0 border-r border-ink-100 bg-white h-screen sticky top-0 px-5 py-6 overflow-y-auto">
      {/* Brand */}
      <div className="flex items-center gap-2 pb-5 border-b border-ink-100 mb-5">
        <div className="w-2.5 h-2.5 rounded-full bg-brand-500" />
        <span className="font-semibold text-ink-900">Meeting Memory</span>
      </div>

      {/* Status */}
      <div className="mb-6">
        <p className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2">
          System
        </p>
        <div className="flex items-center gap-2 text-sm text-ink-600">
          <span className={`w-1.5 h-1.5 rounded-full ${statusColor}`} />
          {statusText}
        </div>
      </div>

      {/* Audio upload */}
      <div className="mb-6">
        <p className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2">
          Add Meeting
        </p>

        <input
          type="file"
          accept=".mp3,.wav,.m4a,.flac,.ogg,.webm"
          onChange={(e) => setAudioFile(e.target.files[0] || null)}
          className="block w-full text-xs text-ink-600 mb-2 file:mr-2 file:py-1.5 file:px-3 file:rounded-md file:border file:border-ink-200 file:bg-ink-50 file:text-ink-600 file:text-xs file:font-medium hover:file:bg-ink-100"
        />

        {audioFile && (
          <div className="space-y-2">
            <input
              type="text"
              value={meetingTitle}
              onChange={(e) => setMeetingTitle(e.target.value)}
              placeholder="Meeting title"
              className="w-full text-sm border border-ink-200 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
            />
            <input
              type="date"
              value={meetingDate}
              onChange={(e) => setMeetingDate(e.target.value)}
              className="w-full text-sm border border-ink-200 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
            />
            <button
              onClick={handleTranscribe}
              disabled={transcribing}
              className="w-full text-sm font-medium text-white bg-brand-500 hover:bg-brand-600 rounded-md py-2 transition-colors disabled:opacity-70"
            >
              {transcribing ? "Transcribing..." : "Transcribe & Index"}
            </button>
          </div>
        )}

        {transcribeResult && (
          <div className="mt-2">
            {transcribeResult.status === "success" ? (
              <div className="text-xs text-green-700 bg-green-50 border border-green-100 rounded-md px-3 py-2">
                Transcribed and indexed — {transcribeResult.chunks_added} total chunks
              </div>
            ) : (
              <div className="text-xs text-red-700 bg-red-50 border border-red-100 rounded-md px-3 py-2">
                {transcribeResult.detail || "Transcription failed"}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Re-index */}
      <div className="mb-6">
        <p className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2">
          Pipeline
        </p>
        <button
          onClick={handleReindex}
          disabled={loading}
          className="w-full text-sm font-medium text-ink-600 bg-ink-50 hover:bg-ink-100 border border-ink-200 rounded-md py-2 transition-colors disabled:opacity-50"
        >
          {loading ? "Indexing..." : "Re-index transcripts"}
        </button>
      </div>

      {/* Meetings */}
      <div>
        <p className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2">
          Indexed Meetings
        </p>
        <div className="space-y-1">
          {meetings.map((m, i) => (
            <div
              key={i}
              className="text-sm py-2 border-b border-ink-50 last:border-0"
            >
              <div className="font-medium text-ink-800">{m.title}</div>
              <div className="text-xs text-ink-400 mt-0.5">{m.date}</div>
            </div>
          ))}
          {meetings.length === 0 && (
            <p className="text-sm text-ink-400">No meetings indexed.</p>
          )}
        </div>
      </div>
    </aside>
  )
}