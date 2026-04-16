import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, parseISO } from 'date-fns'
import { CheckCircle, Filter } from 'lucide-react'
import StatusBadge from '../components/StatusBadge'
import { getAnomalies, resolveAnomaly } from '../lib/api'
import clsx from 'clsx'

// ─── Filter bar ───────────────────────────────────────────────────────────────

function FilterBar({ severity, status, onSeverity, onStatus }) {
  const severities = ['All', 'P1', 'P2', 'P3']
  const statuses   = ['all', 'active', 'resolved']

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-2 text-sm text-[#8b949e]">
        <Filter size={14} />
        <span className="font-medium">Severity:</span>
      </div>
      <div className="flex gap-1">
        {severities.map((s) => (
          <button
            key={s}
            onClick={() => onSeverity(s)}
            className={clsx(
              'px-3 py-1 rounded text-xs font-medium transition-colors',
              severity === s
                ? 'bg-blue-600 text-white'
                : 'bg-[#1c2128] text-[#8b949e] hover:text-[#e6edf3]'
            )}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="w-px h-4 bg-[#30363d]" aria-hidden="true" />

      <div className="flex items-center gap-2 text-sm text-[#8b949e]">
        <span className="font-medium">Status:</span>
      </div>
      <div className="flex gap-1">
        {statuses.map((s) => (
          <button
            key={s}
            onClick={() => onStatus(s)}
            className={clsx(
              'px-3 py-1 rounded text-xs font-medium capitalize transition-colors',
              status === s
                ? 'bg-blue-600 text-white'
                : 'bg-[#1c2128] text-[#8b949e] hover:text-[#e6edf3]'
            )}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Skeleton rows ────────────────────────────────────────────────────────────

function SkeletonRows({ count = 5 }) {
  return (
    <tbody className="divide-y divide-[#21262d]">
      {Array.from({ length: count }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: 7 }).map((_, j) => (
            <td key={j} className="px-4 py-3">
              <div className="skeleton h-4 rounded w-full" />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Anomalies() {
  const [severity, setSeverity] = useState('All')
  const [status,   setStatus]   = useState('all')

  const queryClient = useQueryClient()

  const apiParams = {
    ...(severity !== 'All' ? { severity } : {}),
    ...(status   !== 'all' ? { status }   : {}),
  }

  const {
    data: anomalies = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['anomalies', apiParams],
    queryFn:  () => getAnomalies(apiParams),
    refetchInterval: 30_000,
  })

  const { mutate: resolve, variables: resolvingId } = useMutation({
    mutationFn: resolveAnomaly,
    // Optimistic update: mark as resolved immediately in the cache
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['anomalies', apiParams] })
      const previous = queryClient.getQueryData(['anomalies', apiParams])
      queryClient.setQueryData(['anomalies', apiParams], (old = []) =>
        old.map((a) => (a.id === id ? { ...a, status: 'resolved' } : a))
      )
      return { previous }
    },
    onError: (_err, _id, ctx) => {
      queryClient.setQueryData(['anomalies', apiParams], ctx.previous)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['anomalies'] })
    },
  })

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-[#e6edf3]">Anomalies</h1>
        <p className="text-sm text-[#8b949e] mt-0.5">
          Auto-refreshes every 30 seconds. Resolve issues directly from this view.
        </p>
      </div>

      {/* Filter bar */}
      <FilterBar
        severity={severity}
        status={status}
        onSeverity={setSeverity}
        onStatus={setStatus}
      />

      {/* Table card */}
      <div className="card overflow-hidden">
        {isError ? (
          <div className="p-6 text-center text-sm text-red-400">
            {error?.message ?? 'Failed to load anomalies.'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="border-b border-[#30363d]">
                <tr>
                  {['Type', 'Severity', 'Pipeline', 'Description', 'Detected At', 'Status', ''].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-medium text-[#8b949e] uppercase tracking-wider whitespace-nowrap"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>

              {isLoading ? (
                <SkeletonRows />
              ) : (
                <tbody className="divide-y divide-[#21262d]">
                  {anomalies.length === 0 ? (
                    <tr>
                      <td
                        colSpan={7}
                        className="px-4 py-12 text-center text-sm text-[#8b949e]"
                      >
                        No anomalies match the current filters.
                      </td>
                    </tr>
                  ) : (
                    anomalies.map((anomaly) => {
                      const isResolved = anomaly.status === 'resolved'
                      const isResolving = resolvingId === anomaly.id

                      return (
                        <tr
                          key={anomaly.id}
                          className={clsx(
                            'table-row-hover',
                            isResolved && 'opacity-60'
                          )}
                        >
                          {/* Type */}
                          <td className="px-4 py-3 text-sm text-[#e6edf3] whitespace-nowrap">
                            {anomaly.anomaly_type ?? '—'}
                          </td>

                          {/* Severity */}
                          <td className="px-4 py-3">
                            <StatusBadge status={anomaly.severity} />
                          </td>

                          {/* Pipeline */}
                          <td className="px-4 py-3 text-sm text-[#8b949e] whitespace-nowrap">
                            {anomaly.pipeline ?? '—'}
                          </td>

                          {/* Description */}
                          <td className="px-4 py-3 max-w-xs">
                            <span
                              className="text-sm text-[#e6edf3] truncate block"
                              title={anomaly.description}
                            >
                              {anomaly.description?.slice(0, 80) ?? '—'}
                            </span>
                          </td>

                          {/* Detected At */}
                          <td className="px-4 py-3 text-xs text-[#8b949e] whitespace-nowrap font-mono">
                            {anomaly.detected_at
                              ? format(parseISO(anomaly.detected_at), 'MMM d, HH:mm')
                              : '—'}
                          </td>

                          {/* Status */}
                          <td className="px-4 py-3">
                            <StatusBadge status={anomaly.status ?? 'warning'} />
                          </td>

                          {/* Action */}
                          <td className="px-4 py-3 text-right">
                            {!isResolved && (
                              <button
                                onClick={() => resolve(anomaly.id)}
                                disabled={isResolving}
                                className={clsx(
                                  'inline-flex items-center gap-1.5 text-xs font-medium transition-colors',
                                  isResolving
                                    ? 'text-[#484f58] cursor-not-allowed'
                                    : 'text-emerald-400 hover:text-emerald-300'
                                )}
                              >
                                <CheckCircle size={13} />
                                {isResolving ? 'Resolving…' : 'Resolve'}
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              )}
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
