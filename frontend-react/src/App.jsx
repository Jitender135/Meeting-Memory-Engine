import { useState } from "react"
import Sidebar from "./components/Sidebar"
import SearchView from "./components/SearchView"
import ChatView from "./components/ChatView"

function App() {
  const [mode, setMode] = useState("search")

  return (
    <div className="min-h-screen bg-ink-50 text-ink-900 font-sans flex">
      <Sidebar />
      <main className="flex-1 px-8 py-10">
        <h1 className="text-2xl font-semibold">Query your meetings</h1>
        <p className="text-ink-600 mt-1 text-sm mb-6">
          Ask anything across all indexed transcripts.
        </p>

        {/* Mode tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setMode("search")}
            className={`text-sm font-medium px-4 py-2 rounded-md transition-colors ${
              mode === "search"
                ? "bg-ink-900 text-white"
                : "bg-white border border-ink-200 text-ink-600 hover:bg-ink-50"
            }`}
          >
            Search
          </button>
          <button
            onClick={() => setMode("chat")}
            className={`text-sm font-medium px-4 py-2 rounded-md transition-colors ${
              mode === "chat"
                ? "bg-ink-900 text-white"
                : "bg-white border border-ink-200 text-ink-600 hover:bg-ink-50"
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