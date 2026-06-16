import { useState, useEffect } from "react"
import Sidebar from "./components/Sidebar"
import SearchView from "./components/SearchView"
import ChatView from "./components/ChatView"

function App() {
  const [mode, setMode] = useState("search")
  const [dark, setDark] = useState(() => {
    return localStorage.getItem("theme") === "dark"
  })

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add("dark")
      localStorage.setItem("theme", "dark")
    } else {
      document.documentElement.classList.remove("dark")
      localStorage.setItem("theme", "light")
    }
  }, [dark])

  return (
    <div className="min-h-screen bg-ink-50 text-ink-900 font-sans flex">
      <Sidebar />
      <main className="flex-1 px-8 py-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold">Query your meetings</h1>
            <p className="text-ink-600 mt-1 text-sm">
              Ask anything across all indexed transcripts.
            </p>
          </div>

          {/* Dark mode toggle — pill style */}
          <button
            onClick={() => setDark(!dark)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-ink-200 bg-white hover:bg-ink-50 transition-colors"
            title="Toggle dark mode"
          >
            <div className={`w-8 h-4 rounded-full transition-colors relative ${dark ? "bg-brand-500" : "bg-ink-200"}`}>
              <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform ${dark ? "translate-x-4" : "translate-x-0.5"}`} />
            </div>
            <span className="text-xs font-medium text-ink-600">
              {dark ? "Dark" : "Light"}
            </span>
          </button>
        </div>

        {/* Mode tabs */}
        <div className="flex gap-1 mb-6 bg-ink-100 p-1 rounded-lg w-fit">
          <button
            onClick={() => setMode("search")}
            className={`text-sm font-medium px-4 py-1.5 rounded-md transition-all ${
              mode === "search"
                ? "bg-white text-ink-900 shadow-sm"
                : "text-ink-500 hover:text-ink-700"
            }`}
          >
            Search
          </button>
          <button
            onClick={() => setMode("chat")}
            className={`text-sm font-medium px-4 py-1.5 rounded-md transition-all ${
              mode === "chat"
                ? "bg-white text-ink-900 shadow-sm"
                : "text-ink-500 hover:text-ink-700"
            }`}
          >
            Chat
          </button>
        </div>

        {mode === "search" ? <SearchView /> : <ChatView />}
      </main>
    </div>
  )
}

export default App