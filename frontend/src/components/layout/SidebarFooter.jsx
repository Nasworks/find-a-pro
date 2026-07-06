import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Sun, Moon, Smartphone, LogOut } from 'lucide-react';
import { toast } from 'sonner';
import SwitchRoleDialog from './SwitchRoleDialog';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { useViewMode } from '../../context/ViewModeContext';

/**
 * SidebarFooter
 * Bottom section of the sidebar with Switch Role, Theme toggle,
 * View-mode toggle, and Log out.
 */
export default function SidebarFooter({ collapsed, roles }) {
  const { logout } = useAuth();
  const { theme, toggle: toggleTheme } = useTheme();
  const { toggle: toggleViewMode } = useViewMode();
  const navigate = useNavigate();

  const doLogout = async () => { await logout(); navigate('/'); };
  const swapView = () => { toggleViewMode(); toast.success('Switched view mode'); };

  return (
    <div className="border-t border-border p-2 space-y-1">
      <SwitchRoleDialog collapsed={collapsed} roles={roles} />

      <button
        onClick={toggleTheme}
        className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
      >
        {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        {!collapsed && <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>}
      </button>

      <button
        data-testid="sidebar-view-mode-toggle"
        onClick={swapView}
        className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
      >
        <Smartphone className="w-4 h-4 shrink-0" />
        {!collapsed && <span>Mobile view</span>}
      </button>

      <button
        onClick={doLogout}
        className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
      >
        <LogOut className="w-4 h-4" />
        {!collapsed && <span>Log out</span>}
      </button>
    </div>
  );
}
