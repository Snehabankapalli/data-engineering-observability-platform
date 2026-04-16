import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import clsx from 'clsx'

const COLOR_MAP = {
  blue:   { bg: 'bg-blue-500/10',    icon: 'text-blue-400',    border: 'border-blue-500/20' },
  green:  { bg: 'bg-emerald-500/10', icon: 'text-emerald-400', border: 'border-emerald-500/20' },
  orange: { bg: 'bg-amber-500/10',   icon: 'text-amber-400',   border: 'border-amber-500/20' },
  red:    { bg: 'bg-red-500/10',     icon: 'text-red-400',     border: 'border-red-500/20' },
}

const TREND_CONFIG = {
  up:      { Icon: TrendingUp,   className: 'text-emerald-400' },
  down:    { Icon: TrendingDown, className: 'text-red-400'     },
  neutral: { Icon: Minus,        className: 'text-[#8b949e]'   },
}

/**
 * A KPI summary card for dashboard overviews.
 *
 * @param {object}  props
 * @param {string}  props.title    - Metric label
 * @param {string|number} props.value - Primary value to display
 * @param {string}  [props.subtitle] - Supporting text below the value
 * @param {'up'|'down'|'neutral'} [props.trend='neutral'] - Trend direction
 * @param {React.ElementType} [props.icon] - Lucide icon component
 * @param {'blue'|'green'|'orange'|'red'} [props.color='blue'] - Accent color
 */
export default function MetricCard({
  title,
  value,
  subtitle,
  trend = 'neutral',
  icon: IconComponent,
  color = 'blue',
}) {
  const colors = COLOR_MAP[color] ?? COLOR_MAP.blue
  const { Icon: TrendIcon, className: trendClass } = TREND_CONFIG[trend] ?? TREND_CONFIG.neutral

  return (
    <div
      className={clsx(
        'card p-5 flex flex-col gap-3 animate-fade-in',
        'hover:border-[#484f58] transition-colors duration-150'
      )}
    >
      {/* Header row */}
      <div className="flex items-start justify-between">
        <span className="text-sm font-medium text-[#8b949e] leading-none">{title}</span>
        {IconComponent && (
          <div className={clsx('p-2 rounded-md', colors.bg, colors.border, 'border')}>
            <IconComponent size={16} className={colors.icon} />
          </div>
        )}
      </div>

      {/* Value */}
      <div className="flex items-end gap-2">
        <span className="text-2xl font-bold text-[#e6edf3] leading-none tabular-nums">
          {value ?? '—'}
        </span>
        <div className="flex items-center gap-1 mb-0.5">
          <TrendIcon size={14} className={trendClass} />
        </div>
      </div>

      {/* Subtitle */}
      {subtitle && (
        <p className="text-xs text-[#8b949e] leading-snug">{subtitle}</p>
      )}
    </div>
  )
}
