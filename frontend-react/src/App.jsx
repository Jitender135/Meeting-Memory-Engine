import Sidebar from "./components/Sidebar"
import SearchView from "./components/SearchView"

function App() {
  return (
    <div className="min-h-screen bg-ink-50 text-ink-900 font-sans flex">
      <Sidebar />
      <main className="flex-1 px-8 py-10">
        <h1 className="text-2xl font-semibold">Query your meetings</h1>
        <p className="text-ink-600 mt-1 text-sm mb-8">
          Ask anything across all indexed transcripts.
        </p>
        <SearchView />
      </main>
    </div>
  )
}

export default App