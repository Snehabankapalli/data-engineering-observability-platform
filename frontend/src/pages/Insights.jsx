import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Sparkles, ChevronDown, ChevronUp, TrendingUp, Database } from 'lucide-react'
import StatusBadge from '../components/StatusBadge'
import { getInsights } from '../lib/api'
import clsx from 'clsx'

// ─── Priority colors for estimated impact ────────────────────────────────────

const IMPACT_COLORS = {
  P1: 'text-red-400',
  P2: 'text-amber-400',
  P3: 'text-blue-400',
}

// ─── Single insight card ──────────────────────────────────────────────────────

function InsightCard({ insight }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="card p-5 flex flex-col gap-3 hover:border-[#484f58] transition-colors duration-150 animate-fade-in">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 flex-1 min-w-0">
          <Sparkles size={15} className="text-blue-400 mt-0.5 shrink-0" />
          <h3 className="text-sm font-semibold text-[#e6edf3] leading-snug">
            {insight.title}
          </h3>
        </div>
        <StatusBadge status={insight.priority} />
      </div>

      {/* Description */}
      <p className="text-sm text-[#8b949e] leading-relaxed">
        {insight.description}
      </p>

      {/* Estimated impact */}
      {insight.estimated_impact && (
        <div className="flex items-center gap-1.5">
          <TrendingUp size={13} className={IMPACT_COLORS[insight.priority] ?? 'text-blue-400'} />
          <span className="text-xs font-medium text-[#8b949e]">
            Estimated impact:{' '}
            <span className={clsx('font-semibold', IMPACT_COLORS[insight.priority] ?? 'text-blue-400')}>
              {insight.estimated_impact}
            </span>
          </span>
        </div>
      )}

      {/* Recommendation (expandable) */}
      {insight.recommendation && (
        <div>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors font-medium"
          >
            {expanded ? (
              <>
                <ChevronUp size={13} />
                Hide recommendation
              </>
            ) : (
              <>
                <ChevronDown size={13} />
                Show recommendation
              </>
            )}
          </button>

          {expanded && (
            <div className="mt-2 p-3 rounded-md bg-[#0d1117] border border-[#30363d] text-sm text-[#e6edf3] leading-relaxed animate-slide-up">
              {insight.recommendation}
            </div>
          )}
        </div>
      )}

      {/* Source / model tag */}
      {insight.source_model && (
        <div className="flex items-center gap-1.5 pt-1 border-t border-[#21262d]">
          <Database size={11} className="text-[#484f58]" />
          <span className="text-xs text-[#484f58] font-mono">{insight.source_model}</span>
        </div>
      )}
    </div>
  )
}

// ─── Skeleton card ────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="card p-5 space-y-3">
      <div className="flex justify-between">
        <div className="skeleton h-4 w-48 rounded" />
        <div className="skeleton h-5 w-12 rounded-full" />
      </div>
      <div className="skeleton h-3 w-full rounded" />
      <div className="skeleton h-3 w-3/4 rounded" />
      <div className="skeleton h-3 w-24 rounded" />
    </div>
  )
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-20 gap-4 text-center">
      <div className="p-4 rounded-full bg-blue-500/10 border border-blue-500/20">
        <Sparkles size={28} className="text-blue-400" />
      </div>
      <div className="space-y-1">
        <p className="text-base font-semibold text-[#e6edf3]">No insights yet</p>
        <p className="text-sm text-[#8b949e] max-w-xs">
          Connect your data warehouse to get started. Claude AI will analyze your
          pipelines and surface cost, performance, and reliability recommendations.
        </p>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Insights() {
  const { data: insights = [], isLoading, isError, error } = useQuery({
    queryKey: ['insights'],
    queryFn:  getInsights,
    staleTime: 60_000,
  })

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-[#e6edf3]">AI Insights</h1>
        <p className="text-sm text-[#8b949e] mt-0.5">
          Claude-generated recommendations for your data platform
        </p>
      </div>

      {/* Error */}
      {isError && (
        <div className="card p-5 border-red-500/30 bg-red-500/5 text-center">
          <p className="text-sm text-red-400">{error?.message ?? 'Failed to load insights.'}</p>
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {isLoading
          ? Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
          : insights.length === 0
          ? <EmptyState />
          : insights.map((insight) => (
              <InsightCard key={insight.id} insight={insight} />
            ))}
      </div>
    </div>
  )
}
