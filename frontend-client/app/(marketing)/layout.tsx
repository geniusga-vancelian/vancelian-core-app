/**
 * Marketing Layout - Dedicated layout for marketing pages (/site and /p/[slug])
 * No TopBar, No DevBanner - clean marketing pages
 * Uses only Tailwind CSS (no external theme)
 */

import './marketing.css';

/**
 * Marketing Layout - Tailwind CSS Only
 * Simple layout without external theme dependencies
 */
export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-white">
      <main className="w-full">
        {children}
      </main>
    </div>
  );
}

