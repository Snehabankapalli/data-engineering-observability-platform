import clsx from 'clsx'

/**
 * Status-to-style mapping.
 * Each entry: { label, bg, text, dot }
 */
const STATUS_STYLES = {
  healthy:   { label: 'Healthy',   bg: 'bg-emerald-500/15', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  success:   { label: 'Success',   bg: 'bg-emerald-500/15', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  running:   { label: 'Running',   bg: 'bg-blue-500/15',    text: 'text-blue-400',    dot: 'bg-blue-400'    },
  warning:   { label: 'Warning',   bg: 'bg-amber-500/15',   text: 'text-amber-400',   dot: 'bg-amber-400'   },
  degraded:  { label: 'Degraded',  bg: 'bg-amber-500/15',   text: 'text-amber-400',   dot: 'bg-amber-400'   },
  failed:    { label: 'Failed',    bg: 'bg-red-500/15',     text: 'text-red-400',     dot: 'bg-red-400'     },
  error:     { label: 'Error',     bg: 'bg-red-500/15',     text: 'text-red-400',     dot: 'bg-red-400'     },
  resolved:  { label: 'Resolved',  bg: 'bg-[#30363d]',      text: 'text-[#8b949e]',   dot: 'bg-[#8b949e]'   },
  P1:        { label: 'P1',        bg: 'bg-red-500/15',     text: 'text-red-400',     dot: 'bg-red-400'     },
  P2:        { label: 'P2',        bg: 'bg-amber-500/15',   text: 'text-amber-400',   dot: 'bg-amber-400'   },
  P3:        { label: 'P3',        bg: 'bg-blue-500/15',    text: 'text-blue-400',    dot: 'bg-blue-400'    },
}

const FALLBACK = { label: 'Unknown', bg: 'bg-[#30363d]', text: 'text-[#8b949e]', dot: 'bg-[#8b949e]' }

/**
 * Small pill-shaped status indicator.
 *
 * @param {object} props
 * @param {string} props.status - One of the known status keys
 * @param {boolean} [props.showDot=true] - Show the leading dot indicator
 */
export default function StatusBadge({ status, showDot = true }) {
  const style = STATUS_STYLES[status] ?? FALLBACK

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
        style.bg,
        style.text
      )}
    >
      {showDot && (
        <span
          className={clsx('w-1.5 h-1.5 rounded-full shrink-0', style.dot)}
          aria-hidden="true"
        />
      )}
      {style.label}
    </span>
  )
}
