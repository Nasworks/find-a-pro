import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { Sheet, SheetContent, SheetTitle, SheetDescription } from './ui/sheet';
import JobRequestForm from './JobRequestForm';

// Full-screen panel that slides in from the right after the user hits "Book".
export default function BookingPanel({ open, onOpenChange, search, suggestion }) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        hideClose
        className="w-full sm:max-w-none max-w-none p-0 border-0 flex flex-col gap-0"
        data-testid="booking-panel"
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <div className="shrink-0 flex items-center gap-3 px-4 sm:px-6 h-16 border-b border-border bg-background/95 backdrop-blur">
          <button type="button" onClick={() => onOpenChange(false)} data-testid="booking-panel-back" className="p-2 -ml-2 rounded-full hover:bg-accent text-foreground" aria-label="Back to search">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="min-w-0">
            <SheetTitle className="text-base font-semibold text-foreground leading-tight">Book a pro</SheetTitle>
            <SheetDescription className="text-xs text-muted-foreground truncate" data-testid="booking-panel-search">
              {search ? `For “${search}”` : 'Tell us about your job'}
            </SheetDescription>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto overscroll-contain">
          <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6 pb-16">
            {open && (
              <JobRequestForm
                flow
                preset={{ title: search, suggestion }}
                onCancel={() => onOpenChange(false)}
                onNavigate={() => onOpenChange(false)}
              />
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
