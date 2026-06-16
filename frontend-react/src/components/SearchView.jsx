import { useState } from "react"
import { postQuery, postActionItems } from "../lib/api"
import { SkeletonAnswer } from "./Skeleton"

export default function SearchView() {
  const [question, setQuestion] = useState("")
  const [result, setResult] = useState(null)
  const [actionItems, setActionItems] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSearch() {
    if (!question.trim()) return
    setLoading(true)
    setResult(null)
    setActionItems(null)

    const res = await postQuery(question.trim())
    setResult(res)

    if (res.answer) {
      const ai = await postActionItems(question.trim())
      setActionItems(ai)
    }

    setLoading(false)
  }

  return (
    <div className="max-w-3xl">
      {/* Input */}
      <label className="text-xs font-semibold text-ink-400 uppercase tracking-wider block mb-2">
        Question
      </label>
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="What did we decide about the mobile app launch?"
        rows={3}
        className="w-full border border-ink-200 rounded-lg px-4 py-3 text-sm text-ink-900 placeholder:text-ink-400 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 resize-none bg-white"
      />

      <div className="flex gap-3 mt-3">
        <button
          onClick={handleSearch}
          disabled={loading}
          className="flex-1 bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium rounded-lg py-2.5 transition-colors disabled:opacity-70 disabled:cursor-not-allowed"
        >
          {loading ? "Searching..." : "Search"}
        </button>
        <button
          onClick={() => { setQuestion(""); setResult(null); setActionItems(null) }}
          className="px-5 bg-white border border-ink-200 text-ink-600 text-sm font-medium rounded-lg hover:bg-ink-50 transition-colors"
        >
          Clear
        </button>
      </div>
      {/* Loading skeleton */}
      {loading && <SkeletonAnswer />}
      
      {/* Answer */}
      {result && (
        <div className="mt-8">
          <p className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2">
            Answer
          </p>
          <div className="bg-white border border-ink-100 border-l-2 border-l-brand-500 rounded-lg px-5 py-4 text-sm text-ink-800 leading-relaxed whitespace-pre-line">
            {result.answer}
          </div>

          {/* Sources */}
          {result.sources?.length > 0 && (
            <div className="mt-6">
              <p className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2">
                Sources
              </p>
              <div className="space-y-2">
                {result.sources.map((s, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between bg-white border border-ink-100 rounded-lg px-4 py-3"
                  >
                    <div>
                      <div className="text-sm font-medium text-ink-800">{s.title}</div>
                      <div className="text-xs text-ink-400 mt-0.5">{s.date}</div>
                    </div>
                    <span className="text-xs font-medium text-brand-600 bg-brand-50 border border-brand-100 rounded-full px-3 py-1">
                      Rank #{i + 1}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action items */}
          {actionItems?.action_items?.length > 0 && (
            <div className="mt-6">
              <p className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2">
                Action Items
              </p>
              <div className="bg-white border border-ink-100 rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-ink-100 text-left text-xs text-ink-400 uppercase tracking-wider">
                      <th className="px-4 py-2.5 font-semibold">Owner</th>
                      <th className="px-4 py-2.5 font-semibold">Task</th>
                      <th className="px-4 py-2.5 font-semibold">Due</th>
                      <th className="px-4 py-2.5 font-semibold">Meeting</th>
                    </tr>
                  </thead>
                  <tbody>
                    {actionItems.action_items.map((item, i) => (
                      <tr key={i} className="border-b border-ink-50 last:border-0">
                        <td className="px-4 py-3 font-medium text-ink-900 whitespace-nowrap">{item.owner}</td>
                        <td className="px-4 py-3 text-ink-700">{item.task}</td>
                        <td className="px-4 py-3 text-ink-400 whitespace-nowrap">{item.due}</td>
                        <td className="px-4 py-3 text-ink-400 whitespace-nowrap">{item.meeting}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && (
        <div className="mt-10 pt-8 border-t border-ink-100">
          <p className="text-sm font-medium text-ink-400 mb-3">Try one of these</p>
          <div className="space-y-2">
            {[
              "What did we decide about the mobile app launch?",
              "What action items were assigned in Q1?",
              "Who committed to the Android performance fix?",
              "What was the pricing model we agreed on?",
            ].map((ex, i) => (
              <div
                key={i}
                onClick={() => setQuestion(ex)}
                className="text-sm text-ink-500 italic bg-white border border-ink-100 rounded-lg px-4 py-2.5 cursor-pointer hover:border-brand-300 hover:text-ink-700 transition-colors"
              >
                {ex}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}