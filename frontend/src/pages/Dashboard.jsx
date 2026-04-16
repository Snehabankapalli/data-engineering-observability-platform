import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import {
  GitBranch, CheckCircle, AlertTriangle, DollarSign,
} from 'lucide-react'
import { format, parseISO } from 'date-fns'
import MetricCard from '../components/MetricCard'
import StatusBadge from '../components/StatusBadge'
import { getDashboardOverview } from '../lib/api'

// ─── Skeleton helpers ─────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="card p-5 space-y-3">
      <div className="skeleton h-4 w-24 rounded" />
      <div className="skeleton h-8 w-16 rounded" />
      <div className="skeleton h-3 w-32 rounded" />
    </div>
  )
}

function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="skeleton h-4 w-12 rounded" />
      <div className="skeleton h-4 flex-1 rounded" />
      <div className="skeleton h-4 w-16 rounded" />
    </div>
  )
}

// ─── Custom Recharts tooltip ──────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card px-3 py-2 text-xs space-y-1 shadow-xl">
      <p className="text-[#8b949e]">{label}</p>
      <p className="text-emerald-400 font-semibold">
        {payload[0].value}% success
      </p>
    </div>
  )
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['dashboard-overview'],
    queryFn: getDashboardOverview,
    refetchInterval: 60_000,
  })

  if (isError) {
    return (
      <div className="p-8">
        <div className="card p-6 border-red-500/30 bg-red-500/5 text-center space-y-2">
          <p className="text-red-400 font-medium">Failed to load dashboard</p>
          <p className="text-sm text-[#8b949e]">{error?.message ?? 'Unknown error'}</p>
        </div>
      </div>
    )
  }

  const overview    = data ?? {}
  const pipelineTrend = overview.pipeline_trend ?? []
  const recentAnomalies = (overview.recent_anomalies ?? []).slice(0, 5)
  const recentInsights  = (overview.recent_insights ?? []).slice(0, 3)

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-semibold text-[#e6edf3]">Overview</h1>
        <p className="text-sm text-[#8b949e] mt-0.5">
          Pipeline health, cost, and anomaly summary
        </p>
      </div>

      {/* ── KPI row ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <MetricCard
              title="Total Pipelines"
              value={overview.total_pipelines ?? '—'}
              subtitle="Tracked across all warehouses"
              trend="neutral"
              icon={GitBranch}
              color="blue"
            />
            <MetricCard
              title="Success Rate"
              value={
                overview.success_rate != null
                  ? `${overview.success_rate.toFixed(1)}%`
                  : '—'
              }
              subtitle="Last 24 hours"
              trend={
                overview.success_rate >= 95
                  ? 'up'
                  : overview.success_rate >= 80
                  ? 'neutral'
                  : 'down'
              }
              icon={CheckCircle}
              color="green"
            />
            <MetricCard
              title="Active Anomalies"
              value={overview.active_anomalies ?? '—'}
              subtitle={
                overview.p1_count
                  ? `${overview.p1_count} P1 critical`
                  : 'Across all pipelines'
              }
              trend={overview.active_anomalies > 0 ? 'down' : 'up'}
              icon={AlertTriangle}
              color={overview.active_anomalies > 0 ? 'orange' : 'green'}
            />
            <MetricCard
              title="Cost Today"
              value={
                overview.cost_today != null
                  ? `$${overview.cost_today.toFixed(2)}`
                  : '—'
              }
              subtitle="Snowflake credits consumed"
              trend="neutral"
              icon={DollarSign}
              color="orange"
            />
          </>
        )}
      </div>

      {/* ── Bar chart ───────────────────────────────────────────────── */}
      <div className="card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-[#e6edf3]">
          7-Day Pipeline Success Rate
        </h2>
        {isLoading ? (
          <div className="skeleton h-48 rounded" />
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={pipelineTrend} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
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
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: '#ffffff08' }} />
              <Bar
                dataKey="success_rate"
                fill="#10b981"
                radius={[3, 3, 0, 0]}
                maxBarSize={40}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Bottom row ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recent anomalies */}
        <div className="card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-[#e6edf3]">Recent Anomalies</h2>
          {isLoading ? (
            Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
          ) : recentAnomalies.length === 0 ? (
            <p className="text-sm text-[#8b949e] py-4 text-center">No active anomalies.</p>
          ) : (
            <ul className="divide-y divide-[#21262d]">
              {recentAnomalies.map((anomaly) => (
                <li key={anomaly.id} className="py-2.5 flex items-start gap-3">
                  <StatusBadge status={anomaly.severity} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[#e6edf3] truncate">{anomaly.description}</p>
                    <p className="text-xs text-[#8b949e] mt-0.5">{anomaly.pipeline}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* AI insights */}
        <div className="card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-[#e6edf3]">AI Insights</h2>
          {isLoading ? (
            Array.from({ length: 3 }).map((_, i) => <SkeletonRow key={i} />)
          ) : recentInsights.length === 0 ? (
            <p className="text-sm text-[#8b949e] py-4 text-center">
              No insights yet. Connect your warehouse to get started.
            </p>
          ) : (
            <ul className="divide-y divide-[#21262d]">
              {recentInsights.map((insight) => (
                <li key={insight.id} className="py-2.5 flex items-start gap-3">
                  <StatusBadge status={insight.priority} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[#e6edf3] truncate font-medium">
                      {insight.title}
                    </p>
                    <p className="text-xs text-[#8b949e] mt-0.5 line-clamp-2">
                      {insight.description}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
