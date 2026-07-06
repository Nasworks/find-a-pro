import React from 'react';
import { NavLink } from 'react-router-dom';

/**
 * SidebarNavSection
 * Renders a labelled group of NavLinks inside the sidebar.
 * Extracted from Sidebar.jsx to reduce cyclomatic complexity.
 */
export default function SidebarNavSection({ section, items, collapsed, onNavigate }) {
  return (
    <div className="mb-4">
      {!collapsed && (
        <div className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          {section}
        </div>
      )}
      <div className="space-y-0.5">
        {items.map((it) => {
          const testId = `sidebar-nav-${it.label.toLowerCase().replace(/\s+&\s+/g, '-').replace(/\s+/g, '-')}`;
          const Icon = it.icon;
          return (
            <NavLink
              key={it.to}
              to={it.to}
              onClick={() => onNavigate?.()}
              data-testid={testId}
              className={({ isActive }) => {
                const highlight = it.highlight
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90 justify-center shadow-sm shadow-primary/20'
                  : isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent';
                return `group flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${highlight}`;
              }}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {!collapsed && <span className="truncate">{it.label}</span>}
            </NavLink>
          );
        })}
      </div>
    </div>
  );
}
