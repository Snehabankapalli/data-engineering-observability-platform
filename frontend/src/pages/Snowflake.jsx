import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { X, Sparkles } from 'lucide-react'
import QueryTable from '../components/QueryTable'
import { getWarehouseCosts, getSlowQueries, analyzeQuery } from '../lib/api'

// ─── Custom Recharts tooltip ──────────────────────────────────────────────────

function CostTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card px-3 py-2 text-xs space-y-1 shadow-xl">
      <p className="text-[#8b949e]">
        {(() => { try { return format(parseISO(label), 'MMM d, yyyy') } catch { return label } })()}
      </p>
      {payload.map((entry) => (
        <p key={entry.dataKey} style={{ color: entry.color }} className="font-semibold">
          {entry.name}: {entry.value?.toFixed(2)} cr
        </p>
      ))}
    </div>
  )
}

// ─── Analysis modal ───────────────────────────────────────────────────────────

function QueryAnalysisModal({ query, onClose }) {
  const { mutate, isPending, data, error } = useMutation({
    mutationFn: analyzeQuery,
  })

  // Kick off analysis on first render
  useState(() => {
    mutate({
      query_text:        query.query_text,
      warehouse:         query.warehouse_name,
      execution_time_ms: query.execution_time_ms,
    })
  })

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
            <h3 className="font-semibold text-[#e6edf3] text-sm">Query Analysis</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-[#1c2128] text-[#8b949e] hover:text-[#e6edf3] transition-colors"
            aria-label="Close modal"
          >
            <X size={16} />
          </button>
        </div>

        {/* Query preview */}
        <div className="px-5 py-3 bg-[#0d1117] border-b border-[#30363d]">
          <p className="text-xs font-mono text-[#8b949e] line-clamp-3">
            {query.query_text}
          </p>
        </div>

        {/* Body */}
        <div className="overflow-y-auto px-5 py-4 flex-1 space-y-4">
          {isPending && (
            <div className="flex items-center gap-2 text-[#8b949e] py-8 justify-center">
              <svg className="animate-spin h-5 w-5 text-blue-400" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <span className="text-sm">Analyzing with Claude AI...</span>
            </div>
          )}

          {error && (
            <p className="text-sm text-red-400 text-center py-4">
              {error?.message ?? 'Analysis failed.'}
            </p>
          )}

          {data && (
            <>
              {data.analysis && (
                <div>
                  <p className="text-xs font-semibold text-[#8b949e] uppercase tracking-wider mb-2">
                    Analysis
                  </p>
                  <p className="text-sm text-[#e6edf3] leading-relaxed">{data.analysis}</p>
                </div>
              )}

              {data.optimizations?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-[#8b949e] uppercase tracking-wider mb-2">
                    Optimization Suggestions
                  </p>
                  <ul className="space-y-1.5">
                    {data.optimizations.map((opt, i) => (
                      <li key={i} className="flex gap-2 text-sm text-[#e6edf3]">
                        <span className="text-blue-400 shrink-0">•</span>
                        {opt}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Warehouse colors ─────────────────────────────────────────────────────────

const WAREHOUSE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Snowflake() {
  const [selectedQuery, setSelectedQuery] = useState(null)
  const [costWindow, setCostWindow] = useState(30)

  const {
    data: costData = [],
    isLoading: costsLoading,
  } = useQuery({
    queryKey: ['warehouse-costs', costWindow],
    queryFn: () => getWarehouseCosts(costWindow),
  })

  const {
    data: slowQueries = [],
    isLoading: queriesLoading,
  } = useQuery({
    queryKey: ['slow-queries'],
    queryFn: () => getSlowQueries(24),
  })

  // Derive unique warehouse names for the legend
  const warehouses = [
    ...new Set(costData.flatMap((row) => Object.keys(row).filter((k) => k !== 'date'))),
  ]

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-[#e6edf3]">Snowflake</h1>
        <p className="text-sm text-[#8b949e] mt-0.5">
          Warehouse costs, credit usage, and slow query diagnostics
        </p>
      </div>

      {/* ── Cost chart ────────────────────────────────────────────── */}
      <div className="card p-5 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-sm font-semibold text-[#e6edf3]">Warehouse Credits Per Day</h2>
          <div className="flex gap-1">
            {[7, 14, 30].map((d) => (
              <button
                key={d}
                onClick={() => setCostWindow(d)}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  costWindow === d
                    ? 'bg-blue-600 text-white'
                    : 'bg-[#1c2128] text-[#8b949e] hover:text-[#e6edf3]'
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        {costsLoading ? (
          <div className="skeleton h-52 rounded" />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={costData} margin={{ top: 4, right: 16, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#30363d" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fill: '#8b949e', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => {
                  try { return format(parseISO(v), 'MMM d') } catch { return v }
                }}
              />
              <YAxis
                tick={{ fill: '#8b949e', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v}cr`}
              />
              <Tooltip content={<CostTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: '12px', color: '#8b949e', paddingTop: '8px' }}
              />
              {warehouses.map((wh, i) => (
                <Line
                  key={wh}
                  type="monotone"
                  dataKey={wh}
                  stroke={WAREHOUSE_COLORS[i % WAREHOUSE_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
              {/* Fallback when no warehouses are in the data */}
              {warehouses.length === 0 && (
                <Line
                  type="monotone"
                  dataKey="credits"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Slow queries ──────────────────────────────────────────── */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-[#30363d]">
          <h2 className="text-sm font-semibold text-[#e6edf3]">Slow Queries (Last 24h)</h2>
          <p className="text-xs text-[#8b949e] mt-0.5">
            Sorted by execution time. Click Analyze for Claude AI recommendations.
          </p>
        </div>
        <QueryTable
          rows={slowQueries}
          loading={queriesLoading}
          onAnalyze={setSelectedQuery}
        />
      </div>

      {/* Analysis modal */}
      {selectedQuery && (
        <QueryAnalysisModal
          query={selectedQuery}
          onClose={() => setSelectedQuery(null)}
        />
      )}
    </div>
  )
}
