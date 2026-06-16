import { useState, useRef, useEffect } from "react"
import { postChat } from "../lib/api"

export default function ChatView() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function handleSend() {
    if (!input.trim() || loading) return

    const userMessage = { role: "user", content: input.trim() }
    const history = messages.map(({ role, content }) => ({ role, content }))

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setLoading(true)

    const res = await postChat(userMessage.content, history)

    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: res.answer || "Something went wrong.",
        sources: res.sources || [],
      },
    ])
    setLoading(false)
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="max-w-3xl flex flex-col" style={{ minHeight: "60vh" }}>
      {/* Messages */}
      <div className="flex-1 space-y-4 mb-4">
        {messages.length === 0 && (
          <div className="pt-8 border-t border-ink-100">
            <p className="text-sm font-medium text-ink-400 mb-3">Start a conversation</p>
            <div className="space-y-2">
              <div className="text-sm text-ink-500 italic bg-white border border-ink-100 rounded-lg px-4 py-2.5">
                "What did we decide about the mobile app launch?"
              </div>
              <div className="text-sm text-ink-500 italic bg-white border border-ink-100 rounded-lg px-4 py-2.5">
                Then ask: "Who was responsible for that?"
              </div>
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={
                m.role === "user"
                  ? "bg-brand-500 text-white rounded-2xl rounded-br-md px-4 py-2.5 text-sm max-w-[75%]"
                  : "bg-white border border-ink-100 border-l-2 border-l-brand-500 rounded-2xl rounded-bl-md px-4 py-3 text-sm text-ink-800 max-w-[85%] leading-relaxed whitespace-pre-line"
              }
            >
              {m.content}

              {m.sources?.length > 0 && (
                <div className="mt-2.5 pt-2.5 border-t border-ink-100 flex flex-wrap gap-1.5">
                  {m.sources.map((s, j) => (
                    <span
                      key={j}
                      className="text-xs text-ink-400 bg-ink-50 border border-ink-100 rounded-md px-2 py-0.5"
                    >
                      {s.title} · {s.date}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-ink-100 rounded-2xl rounded-bl-md px-4 py-3 text-sm text-ink-400">
              Thinking...
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="mt-6 flex gap-3 items-end border-t border-ink-100 pt-4">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a follow-up question..."
          rows={1}
          className="flex-1 border border-ink-200 rounded-lg px-4 py-3 text-sm text-ink-900 placeholder:text-ink-400 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 resize-none bg-white"
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className="bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium rounded-lg px-5 py-3 transition-colors disabled:opacity-70 disabled:cursor-not-allowed"
        >
          Send
        </button>
        {messages.length > 0 && (
          <button
            onClick={() => setMessages([])}
            className="px-4 py-3 bg-white border border-ink-200 text-ink-600 text-sm font-medium rounded-lg hover:bg-ink-50 transition-colors"
          >
            Reset
          </button>
        )}
      </div>
    </div>
  )
}