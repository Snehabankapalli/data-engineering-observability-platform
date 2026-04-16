import { NavLink, Outlet } from 'react-router-dom'
import {
  Home,
  GitBranch,
  Database,
  AlertTriangle,
  Sparkles,
  Github,
} from 'lucide-react'
import clsx from 'clsx'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard',     Icon: Home          },
  { to: '/dbt',       label: 'dbt Pipelines', Icon: GitBranch     },
  { to: '/snowflake', label: 'Snowflake',      Icon: Database      },
  { to: '/anomalies', label: 'Anomalies',      Icon: AlertTriangle },
  { to: '/insights',  label: 'AI Insights',    Icon: Sparkles      },
]

/**
 * Root layout with a fixed left sidebar and a scrollable main content area.
 * All page routes are rendered via <Outlet />.
 */
export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-[#0d1117]">
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className="flex flex-col w-56 shrink-0 border-r border-[#30363d] bg-[#0d1117]">
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 py-5 border-b border-[#30363d]">
          <span className="text-xl" aria-hidden="true">🔍</span>
          <span className="font-semibold text-[#e6edf3] tracking-tight">
            DE Observer
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-4 space-y-0.5 px-2">
          {NAV_ITEMS.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-100',
                  isActive
                    ? 'bg-blue-600/20 text-blue-400 border-l-2 border-blue-400 pl-[10px]'
                    : 'text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#161b22] border-l-2 border-transparent'
                )
              }
            >
              <Icon size={16} className="shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-[#30363d]">
          <a
            href="https://github.com/Snehabankapalli"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-xs text-[#8b949e] hover:text-[#e6edf3] transition-colors"
          >
            <Github size={14} />
            View on GitHub
          </a>
        </div>
      </aside>

      {/* ── Main content ────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto bg-[#161b22]">
        <Outlet />
      </main>
    </div>
  )
}
