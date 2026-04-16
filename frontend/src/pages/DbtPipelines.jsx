import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { format, parseISO } from 'date-fns'
import { X, Loader2, Sparkles } from 'lucide-react'
import StatusBadge from '../components/StatusBadge'
import { getDbtRuns, getDbtFailures, analyzeDbtRun } from '../lib/api'

// ─── Modal ────────────────────────────────────────────────────────────────────

function AnalysisModal({ title, content, onClose }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="card w-full max-w-2xl max-h-[80vh] flex flex-col animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#30363d]">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-blue-400" />
            <h3 className="font-semibold text-[#e6edf3] text-sm">{title}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-[#1c2128] text-[#8b949e] hover:text-[#e6edf3] transition-colors"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto px-5 py-4 flex-1">
          {content ? (
            <div className="prose prose-invert prose-sm max-w-none">
              <pre className="bg-[#0d1117] rounded-lg p-4 text-sm text-[#e6edf3] whitespace-pre-wrap font-mono leading-relaxed">
                {typeof content === 'string' ? content : JSON.stringify(content, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="flex items-center justify-center py-12 gap-2 text-[#8b949e]">
              <Loader2 size={18} className="animate-spin" />
              <span className="text-sm">Analyzing with Claude AI...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function TableSkeleton({ cols = 5, rows = 5 }) {
  return (
    <div className="p-4 space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-3">
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className="skeleton h-8 flex-1 rounded" />
          ))}
        </div>
      ))}
    </div>
  )
}

// ─── Runs tab ─────────────────────────────────────────────────────────────────

function RunsTab() {
  const { data: runs = [], isLoading, isError, error } = useQuery({
    queryKey: ['dbt-runs'],
    queryFn: () => getDbtRuns(20),
  })

  if (isLoading) return <TableSkeleton />
  if (isError) {
    return (
      <div className="p-6 text-center text-sm text-red-400">
        {error?.message ?? 'Failed to load runs.'}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full">
        <thead className="border-b border-[#30363d]">
          <tr>
            {['Run ID', 'Status', 'Started', 'Duration', 'Rows Affected'].map((h) => (
              <th
                key={h}
                className="px-4 py-3 text-left text-xs font-medium text-[#8b949e] uppercase tracking-wider"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#21262d]">
          {runs.length === 0 ? (
            <tr>
              <td colSpan={5} className="px-4 py-10 text-center text-sm text-[#8b949e]">
                No runs found.
              </td>
            </tr>
          ) : (
            runs.map((run) => (
              <tr key={run.run_id} className="table-row-hover">
                <td className="px-4 py-3 text-xs font-mono text-[#8b949e]">
                  {String(run.run_id).slice(0, 12)}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={run.status} />
                </td>
                <td className="px-4 py-3 text-sm text-[#8b949e] whitespace-nowrap">
                  {run.started_at
                    ? format(parseISO(run.started_at), 'MMM d, HH:mm:ss')
                    : '—'}
                </td>
                <td className="px-4 py-3 text-sm text-[#e6edf3] tabular-nums">
                  {run.duration_seconds != null
                    ? `${run.duration_seconds.toFixed(1)}s`
                    : '—'}
                </td>
                <td className="px-4 py-3 text-sm text-[#e6edf3] tabular-nums">
                  {run.rows_affected?.toLocaleString() ?? '—'}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

// ─── Failures tab ─────────────────────────────────────────────────────────────

function FailuresTab() {
  const [modalState, setModalState] = useState(null) // { title, content }

  const { data: failures = [], isLoading, isError, error } = useQuery({
    queryKey: ['dbt-failures'],
    queryFn: getDbtFailures,
  })

  const { mutate: analyze, isPending } = useMutation({
    mutationFn: analyzeDbtRun,
    onMutate: (runId) => {
      setModalState({ title: `Analyzing run ${String(runId).slice(0, 12)}`, content: null })
    },
    onSuccess: (result) => {
      setModalState((prev) => ({
        ...prev,
        content: result?.analysis ?? JSON.stringify(result, null, 2),
      }))
    },
    onError: (err) => {
      setModalState((prev) => ({
        ...prev,
        content: `Error: ${err?.message ?? 'Analysis failed.'}`,
      }))
    },
  })

  if (isLoading) return <TableSkeleton cols={4} />
  if (isError) {
    return (
      <div className="p-6 text-center text-sm text-red-400">
        {error?.message ?? 'Failed to load failures.'}
      </div>
    )
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead className="border-b border-[#30363d]">
            <tr>
              {['Test Name', 'Model', 'Error Preview', 'Action'].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-medium text-[#8b949e] uppercase tracking-wider"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#21262d]">
            {failures.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-sm text-[#8b949e]">
                  No test failures found.
                </td>
              </tr>
            ) : (
              failures.map((failure) => (
                <tr key={failure.run_id ?? failure.test_name} className="table-row-hover">
                  <td className="px-4 py-3 text-sm font-mono text-[#e6edf3]">
                    {failure.test_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-[#8b949e]">
                    {failure.model_name ?? '—'}
                  </td>
                  <td className="px-4 py-3 max-w-sm">
                    <span
                      className="text-sm text-red-400 font-mono truncate block"
                      title={failure.error_message}
                    >
                      {failure.error_message?.slice(0, 100) ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => analyze(failure.run_id)}
                      disabled={isPending}
                      className="inline-flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 disabled:opacity-50 transition-colors font-medium"
                    >
                      <Sparkles size={12} />
                      Analyze with AI
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {modalState && (
        <AnalysisModal
          title={modalState.title}
          content={modalState.content}
          onClose={() => setModalState(null)}
        />
      )}
    </>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const TABS = ['Runs', 'Failures']

export default function DbtPipelines() {
  const [activeTab, setActiveTab] = useState('Runs')

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-[#e6edf3]">dbt Pipelines</h1>
        <p className="text-sm text-[#8b949e] mt-0.5">
          Run history, test failures, and AI-powered root cause analysis
        </p>
      </div>

      {/* Card with tabs */}
      <div className="card overflow-hidden">
        {/* Tab bar */}
        <div className="flex border-b border-[#30363d] px-4">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === tab
                  ? 'text-blue-400 border-blue-400'
                  : 'text-[#8b949e] border-transparent hover:text-[#e6edf3]'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === 'Runs' ? <RunsTab /> : <FailuresTab />}
      </div>
    </div>
  )
}
