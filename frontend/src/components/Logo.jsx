import React from 'react';
import { Wrench } from 'lucide-react';

export default function Logo({ size = 'md', showText = true }) {
  const sizes = { sm: 'w-8 h-8', md: 'w-10 h-10', lg: 'w-14 h-14' };
  const iconSize = { sm: 'w-4 h-4', md: 'w-5 h-5', lg: 'w-7 h-7' };
  return (
    <div className="flex items-center gap-2.5">
      <div className={`${sizes[size]} rounded-xl bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center text-white shadow-lg shadow-primary/20`}>
        <Wrench className={iconSize[size]} />
      </div>
      {showText && <span className="text-lg font-bold text-foreground tracking-tight">Dispatchr</span>}
    </div>
  );
}
