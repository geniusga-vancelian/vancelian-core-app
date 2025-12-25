'use client';

import { useEffect } from 'react';

/**
 * Demo20Head - Client component to inject CSS links for demo20 theme
 * Next.js App Router doesn't support <link> tags in layout body,
 * so we inject them client-side
 */
export function Demo20Head() {
  useEffect(() => {
    // List of CSS files to load
    const cssFiles = [
      '/theme/assets/fonts/unicons/unicons.css',
      '/theme/assets/css/plugins.css',
      '/theme/style.css',
      '/theme/assets/css/colors/purple.css',
      '/theme/assets/css/fonts/urbanist.css',
    ];

    // Inject CSS links
    cssFiles.forEach((href) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;
      
      // Check if link already exists
      if (!document.querySelector(`link[href="${href}"]`)) {
        document.head.appendChild(link);
      }
    });

    // Inject inline styles from demo20.html
    const styleId = 'demo20-inline-styles';
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style');
      style.id = styleId;
      style.textContent = `
        .language-select .nav-link {
          color: #ffffff;
        }
        .language-select .nav-link:hover {
          color: #ffffffb3;
        }
        .navbar-light.fixed.navbar-stick .language-select .nav-link {
          color: #343f52;
        }
        .navbar-light.fixed.navbar-stick .language-select .nav-link:hover,
        .navbar-light.fixed.navbar-stick .language-select .nav-link:after,
        .navbar-light.fixed.navbar-stick .nav-link:hover {
          color: #747ed1;
        }
        @media (min-width: 992px) {
          .navbar-expand-lg.navbar-light .dropdown:not(.dropdown-submenu) > .dropdown-toggle:after {
            color: #747ed1;
          }
        }
        @media (max-width: 991.98px) {
          .navbar-expand-lg .navbar-collapse .dropdown-toggle:after {
            color: #ffffff !important;
          }
        }
      `;
      document.head.appendChild(style);
    }

    // Set body class from demo20.html
    document.body.classList.add('!font-Urbanist');
    document.body.style.fontSize = '0.85rem';

    // Cleanup function
    return () => {
      // Optional: remove styles on unmount (usually not needed for pages)
      // cssFiles.forEach((href) => {
      //   const link = document.querySelector(`link[href="${href}"]`);
      //   if (link) link.remove();
      // });
    };
  }, []);

  return null; // This component doesn't render anything
}


