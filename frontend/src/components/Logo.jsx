import React from 'react';
import { Link } from 'react-router-dom';

/**
 * Pro Finder NZ brand mark.
 * Icon = stylised silver-fern frond inside the app's primary→blue gradient badge.
 * Wordmark = "Pro Finder" + a small "NZ" chip that echoes the accent color.
 */
function FernMark({ className = 'w-5 h-5' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {/* central frond stem */}
      <path d="M12 21 C 12 15, 13 9, 17 4" />
      {/* leaflets on the right side */}
      <path d="M14.6 8.2 C 16.2 8.6, 17.4 8.2, 18.4 6.8" />
      <path d="M13.6 11 C 15.4 11.6, 16.8 11.4, 17.9 10" />
      <path d="M12.9 13.9 C 14.7 14.6, 16.1 14.5, 17 13.2" />
      <path d="M12.4 17 C 13.9 17.7, 15.1 17.7, 15.9 16.6" />
      {/* leaflets on the left side (mirror, offset) */}
      <path d="M14 9.6 C 12.5 9.4, 11.4 8.8, 10.7 7.4" />
      <path d="M13.2 12.4 C 11.6 12.4, 10.5 11.9, 9.7 10.6" />
      <path d="M12.6 15.3 C 11 15.4, 9.9 15, 9.1 13.8" />
      <path d="M12.2 18.1 C 10.8 18.4, 9.7 18.1, 9 17.1" />
    </svg>
  );
}

export default function Logo({ size = 'md', showText = true, linkTo = '/' }) {
  const badge = { sm: 'w-8 h-8', md: 'w-10 h-10', lg: 'w-14 h-14' }[size];
  const fern = { sm: 'w-4 h-4', md: 'w-5 h-5', lg: 'w-7 h-7' }[size];
  const wordSize = { sm: 'text-base', md: 'text-lg', lg: 'text-2xl' }[size];
  const chipSize = { sm: 'text-[9px] px-1 py-[1px]', md: 'text-[10px] px-1.5 py-[1px]', lg: 'text-xs px-2 py-0.5' }[size];

  const content = (
    <div className="flex items-center gap-2.5">
      <div className={`${badge} rounded-xl bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center text-white shadow-lg shadow-primary/20`}>
        <FernMark className={fern} />
      </div>
      {showText && (
        <div className="flex items-baseline gap-1.5 leading-none">
          <span className={`${wordSize} font-bold text-foreground tracking-tight`}>Pro Finder</span>
          <span className={`${chipSize} font-semibold rounded-md bg-primary/10 text-primary border border-primary/20 tracking-wider uppercase`}>NZ</span>
        </div>
      )}
    </div>
  );
  if (!linkTo) return content;
  return (
    <Link to={linkTo} data-testid="profinder-logo-home" className="inline-flex items-center hover:opacity-90 transition-opacity" aria-label="Pro Finder NZ home">
      {content}
    </Link>
  );
}
