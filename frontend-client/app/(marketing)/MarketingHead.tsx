'use client';

import { useEffect } from 'react';

/**
 * MarketingHead - Client component to inject CSS links for Sandbox demo25 theme
 * Next.js App Router doesn't support <link> tags in layout body,
 * so we inject them client-side
 * 
 * Demo25 theme uses:
 * - Pink color scheme (/theme/assets/css/colors/pink.css)
 * - Urbanist font family (/theme/assets/css/fonts/urbanist.css)
 */
export function MarketingHead() {
  useEffect(() => {
    // DEV: Log that component is mounting
    if (process.env.NODE_ENV === 'development') {
      console.log('[MarketingHead] Mounting demo25 theme');
    }

    // List of CSS files to load for Sandbox demo25 template (in order)
    const cssFiles = [
      '/theme/assets/fonts/unicons/unicons.css',
      '/theme/assets/css/plugins.css',
      '/theme/style.css',
      '/theme/assets/css/colors/pink.css',
      '/theme/assets/css/fonts/urbanist.css',
    ];

    // Inject CSS links (sequentially to ensure proper loading order)
    cssFiles.forEach((href, index) => {
      // Check if link already exists
      const existingLink = document.querySelector(`link[href="${href}"]`);
      if (!existingLink) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        link.onload = () => {
          if (process.env.NODE_ENV === 'development') {
            console.log(`[MarketingHead] ✓ Loaded CSS (${index + 1}/${cssFiles.length}): ${href}`);
          }
        };
        link.onerror = () => {
          console.error(`[MarketingHead] ✗ Failed to load CSS: ${href}`);
        };
        // Insert before other stylesheets if possible, or append
        const firstLink = document.head.querySelector('link[rel="stylesheet"]');
        if (firstLink && firstLink.parentNode) {
          document.head.insertBefore(link, firstLink);
        } else {
          document.head.appendChild(link);
        }
      } else if (process.env.NODE_ENV === 'development') {
        console.log(`[MarketingHead] CSS already loaded: ${href}`);
      }
    });

    // Inject inline styles for demo25 template (from demo25.html)
    const styleId = 'marketing-demo25-styles';
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style');
      style.id = styleId;
      style.textContent = `
        body.font-Urbanist {
          font-family: 'Urbanist', sans-serif;
          font-size: 0.85rem;
        }
        /* Demo25 specific color overrides */
        .active>.page-link, .page-link.active,
        .plyr__control--overlaid:focus, .plyr__control--overlaid:hover {
          color: #d16b86 !important;
        }
        @media (max-width: 991.98px) {
          .navbar-expand-lg .navbar-collapse .dropdown-toggle:after {
            color: white !important;
          }
        }
        /* Ensure header is above other content */
        header.relative.wrapper {
          position: relative;
          z-index: 9999;
        }
        /* Page frame styling from Sandbox template */
        .page-frame {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
        }
      `;
      document.head.appendChild(style);
    }

    // Set body class for demo25 template (Urbanist font)
    document.body.classList.add('!font-Urbanist');
    document.body.style.fontSize = '0.85rem';

    if (process.env.NODE_ENV === 'development') {
      console.log('[MarketingHead] Applied demo25 theme styles');
    }

    // Cleanup function (optional - usually not needed for pages)
    return () => {
      // CSS links are usually kept for the entire session
    };
  }, []);

  return null; // This component doesn't render anything
}

