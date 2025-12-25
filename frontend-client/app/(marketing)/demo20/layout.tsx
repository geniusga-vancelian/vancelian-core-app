/**
 * Demo20 Layout - Dedicated layout for demo20 page
 * Loads Sandbox theme CSS and JS for demo20 template
 */

import Script from 'next/script';
import type { Metadata } from 'next';
import { Demo20Head } from './Demo20Head';

export const metadata: Metadata = {
  title: 'Demo 20 - Sandbox Template',
  description: 'Modern & Multipurpose Tailwind CSS Template',
};

/**
 * Demo20 Layout Component
 * Loads all CSS and JS assets required for demo20.html template
 */
export default function Demo20Layout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {/* CSS - Injected client-side via Demo20Head */}
      <Demo20Head />

      {/* Body wrapper from demo20.html */}
      <div className="page-frame !bg-[#e0e9fa]">
        <div className="grow shrink-0">
          {children}
        </div>
      </div>

      {/* JS - Loaded via next/script afterInteractive */}
      <Script
        src="/theme/assets/js/plugins.js"
        strategy="afterInteractive"
      />
      <Script
        src="/theme/assets/js/theme.js"
        strategy="afterInteractive"
      />
    </>
  );
}

