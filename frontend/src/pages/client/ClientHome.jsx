import React, { useState } from 'react';
import ServiceSearch from '../../components/ServiceSearch';
import BookingPanel from '../../components/BookingPanel';

export default function ClientHome() {
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(null);
  const [panelOpen, setPanelOpen] = useState(false);

  return (
    <div className="min-h-[calc(100vh-10rem)] flex flex-col items-center justify-center px-5 py-12" data-testid="client-home">
      <div className="w-full max-w-2xl">
        <h1 className="text-center text-3xl md:text-4xl font-bold text-foreground tracking-tight mb-6">
          What do you need <span className="bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">done?</span>
        </h1>
        <ServiceSearch
          value={query}
          onChange={setQuery}
          selected={selected}
          onSelect={setSelected}
          onBook={() => query.trim() && setPanelOpen(true)}
        />
      </div>
      <BookingPanel open={panelOpen} onOpenChange={setPanelOpen} search={query.trim()} suggestion={selected} />
    </div>
  );
}
