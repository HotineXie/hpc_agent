import React from 'react'
import { LayoutDashboard, MessageCircle, ListTodo, Users, ScrollText } from 'lucide-react'

export const PROJECT_TABS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'chat',     label: 'Chat',     icon: MessageCircle },
  { id: 'work',     label: 'Work',     icon: ListTodo },
  { id: 'team',     label: 'Team',     icon: Users },
  { id: 'logs',     label: 'Logs',     icon: ScrollText },
]

export default function ProjectTabSidebar({ activeTab, onTabChange, counts = {} }) {
  return (
    <nav
      aria-label="Project sections"
      className="shrink-0 w-14 sm:w-48 border-r border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 overflow-y-auto flex flex-col py-3"
    >
      {PROJECT_TABS.map(t => {
        const Icon = t.icon
        const badge = counts[t.id]
        const isActive = activeTab === t.id
        return (
          <button
            key={t.id}
            onClick={() => onTabChange(t.id)}
            className={`flex items-center gap-3 px-3 sm:px-4 py-2.5 text-sm font-medium transition-colors border-l-2 ${
              isActive
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300'
                : 'border-transparent text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-900 dark:hover:text-neutral-100'
            }`}
            title={t.label}
          >
            <Icon className="w-4 h-4 shrink-0" />
            <span className="hidden sm:inline flex-1 text-left">{t.label}</span>
            {typeof badge === 'number' && badge > 0 && (
              <span className="hidden sm:inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-200 text-[11px] font-semibold">
                {badge > 99 ? '99+' : badge}
              </span>
            )}
          </button>
        )
      })}
    </nav>
  )
}
