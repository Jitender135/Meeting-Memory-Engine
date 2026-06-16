export function SkeletonLine({ width = "w-full", height = "h-4" }) {
  return (
    <div className={`${width} ${height} bg-ink-100 rounded-md animate-pulse`} />
  )
}

export function SkeletonAnswer() {
  return (
    <div className="mt-8">
      <p className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2">
        Answer
      </p>
      <div className="bg-white border border-ink-100 border-l-2 border-l-brand-500 rounded-lg px-5 py-4 space-y-2">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-5/6" />
        <SkeletonLine width="w-4/6" />
      </div>

      <div className="mt-6">
        <p className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2">
          Sources
        </p>
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center justify-between bg-white border border-ink-100 rounded-lg px-4 py-3">
              <div className="space-y-1.5 flex-1">
                <SkeletonLine width="w-48" height="h-3.5" />
                <SkeletonLine width="w-24" height="h-3" />
              </div>
              <SkeletonLine width="w-16" height="h-6" />
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6">
        <p className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2">
          Action Items
        </p>
        <div className="bg-white border border-ink-100 rounded-lg overflow-hidden">
          <div className="px-4 py-2.5 border-b border-ink-100">
            <SkeletonLine width="w-full" height="h-3" />
          </div>
          {[1, 2, 3].map((i) => (
            <div key={i} className="px-4 py-3 border-b border-ink-50 last:border-0 flex gap-4">
              <SkeletonLine width="w-16" height="h-3.5" />
              <SkeletonLine width="w-48" height="h-3.5" />
              <SkeletonLine width="w-20" height="h-3.5" />
              <SkeletonLine width="w-32" height="h-3.5" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}