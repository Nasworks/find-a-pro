import React, { useState } from 'react';
import { PanelRight } from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import { useViewMode } from '../context/ViewModeContext';

// On desktop renders children inline; on phones/tablets moves them into a slide-out pane.
export const SidePane = ({ children, title, label, icon: Icon = PanelRight, side = 'right', testid = 'side-pane', open: openProp, onOpenChange, hideTrigger = false }) => {
  const { compact } = useViewMode();
  const [openState, setOpenState] = useState(false);
  const open = openProp ?? openState;
  const setOpen = onOpenChange ?? setOpenState;
  if (!compact) return children;
  return (
    <>
      {!hideTrigger && (
        <button
          onClick={() => setOpen(true)}
          data-testid={`${testid}-trigger`}
          className="side-pane-fab fixed right-4 z-30 inline-flex items-center gap-2 h-11 px-4 rounded-full bg-foreground text-background text-sm font-semibold shadow-lg shadow-black/20 active:scale-95 transition-transform"
        >
          <Icon className="w-4 h-4" /> {label}
        </button>
      )}
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side={side} className="side-pane-sheet w-[90vw] max-w-md p-0 flex flex-col" data-testid={`${testid}-sheet`}>
          <SheetHeader className="px-5 py-4 border-b border-border text-left">
            <SheetTitle>{title || label}</SheetTitle>
          </SheetHeader>
          <div className="flex-1 overflow-y-auto overscroll-contain p-4 space-y-4">{children}</div>
        </SheetContent>
      </Sheet>
    </>
  );
};

export default SidePane;
