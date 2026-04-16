import { useState, useMemo } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import clsx from 'clsx'

const PAGE_SIZE = 10

/**
 * Truncate a string to maxLen characters, appending "…" if cut.
 * @param {string} text
 * @param {number} maxLen
 */
function truncate(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? `${text.slice(0, maxLen)}…` : text
}

/**
 * Format a duration in milliseconds to a human-readable string.
 * @param {number} ms
 */
function formatDuration(ms) {
  if (ms == null) return '—'
  if (ms < 1_000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1_000).toFixed(1)}s`
  return `${(ms / 60_000).toFixed(1)}m`
}

/**
 * Sortable, paginated table for Snowflake slow queries.
 *
 * @param {object}   props
 * @param {Array}    props.rows          - Query rows from the API
 * @param {boolean}  [props.loading]     - Show loading skeleton
 * @param {Function} [props.onAnalyze]   - Called with a row when "Analyze" is clicked
 */
export default function QueryTable({ rows = [], loading = false, onAnalyze }) {
  const [sortKey, setSortKey]   = useState('execution_time_ms')
  const [sortDir, setSortDir]   = useState('desc')
  const [page, setPage]         = useState(1)

  const handleSort = (key) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
    setPage(1)
  }

  const sorted = useMemo(() => {
    if (!rows.length) return []
    return [...rows].sort((a, b) => {
      const av = a[sortKey] ?? 0
      const bv = b[sortKey] ?? 0
      if (av < bv) return sortDir === 'asc' ? -1 : 1
      if (av > bv) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [rows, sortKey, sortDir])

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE))
  const pageRows = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const SortIcon = ({ colKey }) => {
    if (colKey !== sortKey) return <ChevronsUpDown size={12} className="text-[#484f58]" />
    return sortDir === 'asc'
      ? <ChevronUp size={12} className="text-blue-400" />
      : <ChevronDown size={12} className="text-blue-400" />
  }

  const HeaderCell = ({ colKey, label, sortable = false, align = 'left' }) => (
    <th
      className={clsx(
        'px-4 py-3 text-xs font-medium text-[#8b949e] uppercase tracking-wider whitespace-nowrap',
        align === 'right' ? 'text-right' : 'text-left',
        sortable && 'cursor-pointer select-none hover:text-[#e6edf3] transition-colors'
      )}
      onClick={sortable ? () => handleSort(colKey) : undefined}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {sortable && <SortIcon colKey={colKey} />}
      </span>
    </th>
  )

  if (loading) {
    return (
      <div className="space-y-2 p-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="skeleton h-10 rounded" />
        ))}
      </div>
    )
  }

  return (
    <div className="flex flex-col">
      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead className="border-b border-[#30363d]">
            <tr>
              <HeaderCell colKey="start_time"         label="Time"       />
              <HeaderCell colKey="query_text"         label="Query"      />
              <HeaderCell colKey="warehouse_name"     label="Warehouse"  />
              <HeaderCell colKey="execution_time_ms"  label="Duration"   sortable />
              <HeaderCell colKey="credits_used"       label="Cost"       sortable align="right" />
              {onAnalyze && <th className="px-4 py-3" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#21262d]">
            {pageRows.length === 0 ? (
              <tr>
                <td
                  colSpan={onAnalyze ? 6 : 5}
                  className="px-4 py-10 text-center text-sm text-[#8b949e]"
                >
                  No queries found.
                </td>
              </tr>
            ) : (
              pageRows.map((row, idx) => (
                <tr key={row.query_id ?? idx} className="table-row-hover">
                  {/* Time */}
                  <td className="px-4 py-3 text-xs text-[#8b949e] whitespace-nowrap font-mono">
                    {row.start_time
                      ? format(parseISO(row.start_time), 'MMM d, HH:mm')
                      : '—'}
                  </td>

                  {/* Query text — truncated with title tooltip */}
                  <td className="px-4 py-3 max-w-xs">
                    <span
                      className="text-sm text-[#e6edf3] font-mono cursor-default"
                      title={row.query_text}
                    >
                      {truncate(row.query_text, 80)}
                    </span>
                  </td>

                  {/* Warehouse */}
                  <td className="px-4 py-3 text-sm text-[#8b949e] whitespace-nowrap">
                    {row.warehouse_name ?? '—'}
                  </td>

                  {/* Duration */}
                  <td className="px-4 py-3 text-sm text-[#e6edf3] whitespace-nowrap tabular-nums">
                    {formatDuration(row.execution_time_ms)}
                  </td>

                  {/* Cost */}
                  <td className="px-4 py-3 text-sm text-right text-[#e6edf3] whitespace-nowrap tabular-nums">
                    {row.credits_used != null
                      ? `${row.credits_used.toFixed(4)} cr`
                      : '—'}
                  </td>

                  {/* Analyze action */}
                  {onAnalyze && (
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => onAnalyze(row)}
                        className="text-xs text-blue-400 hover:text-blue-300 transition-colors font-medium"
                      >
                        Analyze
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {sorted.length > PAGE_SIZE && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-[#30363d]">
          <span className="text-xs text-[#8b949e]">
            {sorted.length} queries — page {page} of {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1 rounded hover:bg-[#1c2128] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label="Previous page"
            >
              <ChevronLeft size={16} className="text-[#8b949e]" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1 rounded hover:bg-[#1c2128] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label="Next page"
            >
              <ChevronRight size={16} className="text-[#8b949e]" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
