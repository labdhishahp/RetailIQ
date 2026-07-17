export default function Skeleton({ className = '', variant = 'rect' }) {
  const base = 'animate-pulse bg-slate-200 dark:bg-slate-700'
  const shapes = {
    rect: 'rounded-lg',
    circle: 'rounded-full',
    text: 'rounded h-4',
  }

  return <div className={`${base} ${shapes[variant]} ${className}`} />
}

export function SkeletonCard() {
  return (
    <div className="rounded-2xl p-5 bg-white dark:bg-slate-900 shadow-premium border border-slate-200/60 dark:border-slate-700/60 space-y-3">
      <Skeleton className="h-4 w-24" variant="text" />
      <Skeleton className="h-8 w-32" variant="text" />
      <Skeleton className="h-3 w-20" variant="text" />
    </div>
  )
}

export function SkeletonTable({ rows = 5, cols = 5 }) {
  return (
    <div className="space-y-3">
      <div className="flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" variant="text" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-10 flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}
