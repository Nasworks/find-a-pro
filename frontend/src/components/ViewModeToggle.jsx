import React from 'react';
import { Monitor, Smartphone } from 'lucide-react';
import { useViewMode } from '../context/ViewModeContext';
import { toast } from 'sonner';

/**
 * ViewModeToggle
 * Circular icon button that toggles between desktop and mobile view modes.
 *
 * Props:
 *   variant?: 'icon' | 'chip'     — 'icon' = round button, 'chip' = pill with label. default 'icon'.
 *   className?
 */
export default function ViewModeToggle({ variant = 'icon', className = '' }) {
  const { mode, toggle } = useViewMode();
  const isMobile = mode === 'mobile';
  const Icon = isMobile ? Monitor : Smartphone;
  const label = isMobile ? 'Desktop' : 'Mobile';
  const tooltip = isMobile ? 'Switch to desktop view' : 'Switch to mobile view';

  const handle = () => {
    toggle();
    toast.success(`Switched to ${isMobile ? 'desktop' : 'mobile'} view`, { duration: 1500 });
  };

  if (variant === 'chip') {
    return (
      <button
        type="button"
        data-testid="view-mode-toggle"
        onClick={handle}
        title={tooltip}
        aria-label={tooltip}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-border text-foreground hover:bg-accent hover:border-primary/40 transition-colors ${className}`}
      >
        <Icon className="w-3.5 h-3.5" />
        <span>{label}</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      data-testid="view-mode-toggle"
      onClick={handle}
      title={tooltip}
      aria-label={tooltip}
      className={`relative inline-flex items-center justify-center w-9 h-9 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-accent hover:border-primary/40 transition-colors ${className}`}
    >
      <Icon className="w-4 h-4" />
      <span className="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-primary/10 border border-background flex items-center justify-center" aria-hidden>
        <span className="w-1.5 h-1.5 rounded-full bg-primary" />
      </span>
    </button>
  );
}
