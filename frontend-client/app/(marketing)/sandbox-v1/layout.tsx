import type { Metadata } from 'next';
import Script from 'next/script';

export const metadata: Metadata = {
  title: 'Sandbox V1 - Marketing Page',
  description: 'Marketing page built with Sandbox template blocks',
};

/**
 * Isolated layout for sandbox-v1 page
 * 
 * CSS Files loaded (from /theme/assets):
 * 1. /theme/assets/fonts/unicons/unicons.css - Icon font (Unicons)
 * 2. /theme/assets/css/fonts/thicccboi.css - Main font family
 * 3. /theme/assets/css/plugins.css - Plugin styles (Bootstrap, etc.)
 * 4. /theme/style.css - Main template styles
 * 5. /theme/assets/css/colors/yellow.css - Yellow color theme
 * 
 * JS Files loaded (from /theme/assets/js):
 * 1. /theme/assets/js/plugins.js - Bootstrap and other plugins
 * 2. /theme/assets/js/theme.js - Theme-specific JavaScript (menu, offcanvas, etc.)
 */
export default function SandboxV1Layout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* Template CSS files - loaded from public/theme/assets */}
      <link rel="stylesheet" type="text/css" href="/theme/assets/fonts/unicons/unicons.css" />
      <link rel="stylesheet" type="text/css" href="/theme/assets/css/fonts/thicccboi.css" />
      <link rel="stylesheet" href="/theme/assets/css/plugins.css" />
      <link rel="stylesheet" href="/theme/style.css" />
      <link rel="stylesheet" href="/theme/assets/css/colors/yellow.css" />
      
      {/* Template JS files - loaded via next/script for proper Next.js integration */}
      <Script src="/theme/assets/js/plugins.js" strategy="afterInteractive" />
      <Script src="/theme/assets/js/theme.js" strategy="afterInteractive" />
      
      {/* Template body class and styles */}
      <style dangerouslySetInnerHTML={{
        __html: `
          body.font-THICCCBOI {
            font-family: 'THICCCBOI', sans-serif;
            font-size: 0.85rem;
          }
          /* Ensure header is above other content */
          header.relative.wrapper {
            position: relative;
            z-index: 9999;
          }
        `
      }} />
      
      {children}
    </>
  );
}
