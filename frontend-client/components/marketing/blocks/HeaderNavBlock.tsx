/**
 * Header Nav Block - Navigation header from Strapi CMS
 * Tailwind-only, no external dependencies
 */

'use client';

import Link from 'next/link';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import { getMediaUrl, StrapiMedia } from '@/lib/cms';

export interface HeaderNavBlockProps {
  logo_text?: string;
  logo?: StrapiMedia;
  links?: Array<{ label: string; href: string; is_external?: boolean }>;
  primary_cta?: { label: string; href: string; is_external?: boolean };
  cta_label?: string;
  cta_href?: string;
  theme?: 'light' | 'dark';
  sticky?: boolean;
}

export function HeaderNavBlock({
  logo_text = 'Sandbox',
  logo,
  links = [],
  primary_cta,
  cta_label,
  cta_href,
  theme = 'light',
  sticky = true,
}: HeaderNavBlockProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [svgLoading, setSvgLoading] = useState(false);
  const [useInlineSvg, setUseInlineSvg] = useState(false);
  
  // DEV ONLY: Debug logging
  if (process.env.NODE_ENV === 'development') {
    console.log('[HeaderNavBlock] Rendering', {
      logo_text,
      hasLogo: !!logo,
      linksCount: links.length,
      links: links, // Afficher les liens complets pour debug
      theme,
      sticky,
    });
  }
  
  // Get current locale from searchParams, default to 'en'
  const currentLocale = (searchParams.get('locale') || 'en') as 'en' | 'fr' | 'it';
  const logoUrl = getMediaUrl(logo);

  // Load SVG and convert to white
  useEffect(() => {
    if (!logoUrl) {
      setSvgContent(null);
      setUseInlineSvg(false);
      return;
    }

    // Check if URL is SVG
    const isSvg = logoUrl.toLowerCase().endsWith('.svg') || logoUrl.toLowerCase().includes('.svg');
    
    if (!isSvg) {
      // If not SVG, use CSS filter instead
      setSvgContent(null);
      setUseInlineSvg(false);
      return;
    }

    setSvgLoading(true);
    
    // Fetch SVG content
    fetch(logoUrl)
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to fetch SVG');
        }
        return response.text();
      })
      .then((svgText) => {
        // Parse and modify SVG to make it white
        let modifiedSvg = svgText;
        
        // Replace fill attributes (but not fill="none")
        modifiedSvg = modifiedSvg.replace(/\bfill="[^"]*"/g, (match) => {
          if (match === 'fill="none"') return match;
          return 'fill="#FFFFFF"';
        });
        
        // Replace fill attributes without quotes
        modifiedSvg = modifiedSvg.replace(/\bfill=[^"\s>]*/g, (match) => {
          if (match.includes('none')) return match;
          return 'fill="#FFFFFF"';
        });
        
        // Replace stroke attributes (but not stroke="none")
        modifiedSvg = modifiedSvg.replace(/\bstroke="[^"]*"/g, (match) => {
          if (match === 'stroke="none"') return match;
          return 'stroke="#FFFFFF"';
        });
        
        // Replace stroke attributes without quotes
        modifiedSvg = modifiedSvg.replace(/\bstroke=[^"\s>]*/g, (match) => {
          if (match.includes('none')) return match;
          return 'stroke="#FFFFFF"';
        });
        
        // If no fill/stroke found, add fill to root SVG element
        if (!modifiedSvg.includes('fill=') && !modifiedSvg.includes('stroke=')) {
          modifiedSvg = modifiedSvg.replace(/<svg([^>]*)>/, '<svg$1 fill="#FFFFFF">');
        }
        
        // Validate that we have a proper SVG structure
        if (modifiedSvg && modifiedSvg.trim().startsWith('<svg')) {
          // Double check: try to parse it as HTML to ensure it's valid
          if (typeof window !== 'undefined') {
            const parser = new DOMParser();
            const doc = parser.parseFromString(modifiedSvg, 'image/svg+xml');
            const parseError = doc.querySelector('parsererror');
            
            if (parseError) {
              throw new Error('SVG parsing failed');
            }
          }
          
          setSvgContent(modifiedSvg);
          setUseInlineSvg(true);
          setSvgLoading(false);
          
          if (process.env.NODE_ENV === 'development') {
            console.log('[HeaderNavBlock] SVG loaded and modified successfully', {
              svgLength: modifiedSvg.length,
              hasFill: modifiedSvg.includes('fill='),
              hasStroke: modifiedSvg.includes('stroke=')
            });
          }
        } else {
          throw new Error('Invalid SVG content after modification');
        }
      })
      .catch((error) => {
        if (process.env.NODE_ENV === 'development') {
          console.warn('[HeaderNavBlock] Failed to load SVG, using CSS filter fallback:', error);
        }
        setSvgContent(null);
        setUseInlineSvg(false);
        setSvgLoading(false);
      });
  }, [logoUrl]);

  // Handle language change
  const handleLocaleChange = (newLocale: 'en' | 'fr' | 'it') => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('locale', newLocale);
    router.push(`${pathname}?${params.toString()}`);
  };

  // Brand-based styles - fully transparent background
  const bgClass = 'bg-transparent';
  const textClass = 'text-brand-white';
  const linkHoverClass = 'hover:text-brand-white/80';
  
  const langButtonActiveClass = 'bg-brand-white/20 text-brand-white';
  const langButtonInactiveClass = 'text-brand-white hover:opacity-70';
  const borderClass = 'border-brand-white/20';

  // Header with fully transparent background (no overlay, no blur)
  const headerClasses = `w-full relative ${bgClass} transition-all duration-300 ${
    sticky ? 'sticky top-0 z-50' : 'relative z-50'
  }`;

  // Check if link is active based on pathname
  const isLinkActive = (href: string): boolean => {
    if (!href) return false;
    // Remove query params and hash for comparison
    const cleanHref = href.split('?')[0].split('#')[0];
    const cleanPathname = pathname.split('?')[0].split('#')[0];
    
    // Exact match or starts with (for nested routes)
    return cleanPathname === cleanHref || (cleanHref !== '/' && cleanPathname.startsWith(cleanHref));
  };

  return (
    <header className={headerClasses}>
      <div className="max-w-[1400px] mx-auto px-6 md:px-8 py-4 relative z-10">
        <nav className="flex items-center justify-between h-16 md:h-20">
          {/* Logo */}
          <div className="flex-shrink-0">
            <Link href="/p/home" className="flex items-center">
              {logoUrl ? (
                useInlineSvg && svgContent ? (
                  // Render SVG inline with white color (only when successfully loaded)
                  <div
                    className="h-8 md:h-10 w-auto flex items-center [&_svg]:h-full [&_svg]:w-auto"
                    style={{ 
                      minWidth: '32px',
                      minHeight: '32px',
                      display: 'flex',
                      alignItems: 'center'
                    }}
                  >
                    <div
                      dangerouslySetInnerHTML={{ __html: svgContent }}
                      style={{ 
                        width: '100%',
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                    />
                  </div>
                ) : (
                  // Fallback: Use CSS filter (always works, even during loading)
                  <img
                    src={logoUrl}
                    alt={logo_text || 'Logo'}
                    className="h-8 md:h-10 w-auto"
                    style={{ filter: 'brightness(0) invert(1)' }}
                    onError={(e) => {
                      if (process.env.NODE_ENV === 'development') {
                        console.warn('[HeaderNavBlock] Image failed to load:', logoUrl);
                      }
                    }}
                  />
                )
              ) : (
                <span className={`text-xl md:text-2xl font-bold font-avenir ${textClass} uppercase tracking-tight`}>
                  {logo_text || 'ARQUANTIX'}
                </span>
              )}
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          {links && links.length > 0 && (
            <div className="hidden md:flex items-center space-x-8 lg:space-x-10">
              {links.map((link, index) => {
                // Handle both direct object and nested structure from Strapi
                const linkLabel = typeof link === 'object' && link !== null 
                  ? (link.label || (link as any).label)
                  : null;
                const linkHref = typeof link === 'object' && link !== null
                  ? (link.href || (link as any).href)
                  : null;
                const linkIsExternal = typeof link === 'object' && link !== null
                  ? (link.is_external !== undefined ? link.is_external : (link as any).is_external)
                  : false;

                if (!linkLabel || !linkHref) {
                  if (process.env.NODE_ENV === 'development') {
                    console.warn('[HeaderNavBlock] Invalid link format', link);
                  }
                  return null;
                }

                const active = !linkIsExternal && isLinkActive(linkHref);

                return (
                  <Link
                    key={index}
                    href={linkHref}
                    className={`${textClass} ${linkHoverClass} text-sm font-avenir font-medium uppercase tracking-wide transition-colors relative ${
                      active ? 'after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[1px] after:bg-brand-white' : ''
                    }`}
                    target={linkIsExternal ? '_blank' : undefined}
                    rel={linkIsExternal ? 'noopener noreferrer' : undefined}
                  >
                    {linkLabel}
                  </Link>
                );
              })}
            </div>
          )}

          {/* CTA Button + Language Selector + Mobile Menu Button */}
          <div className="flex items-center space-x-4 md:space-x-6">
            {/* Primary CTA Button */}
            {(primary_cta || (cta_label && cta_href)) && (
              <div className="hidden md:block">
                {primary_cta ? (
                  primary_cta.is_external ? (
                    <a
                      href={primary_cta.href}
                      className="btn-primary"
                      target="_blank"
                      rel="noreferrer"
                    >
                      {primary_cta.label}
                    </a>
                  ) : (
                    <Link
                      href={primary_cta.href}
                      className="btn-primary"
                    >
                      {primary_cta.label}
                    </Link>
                  )
                ) : cta_href ? (
                  <Link
                    href={cta_href}
                    className="btn-primary"
                  >
                    {cta_label}
                  </Link>
                ) : null}
              </div>
            )}

            {/* Language Selector */}
            <div className={`flex items-center space-x-1 rounded-xl border ${borderClass} p-1`}>
              {(['en', 'fr', 'it'] as const).map((loc) => (
                <button
                  key={loc}
                  onClick={() => handleLocaleChange(loc)}
                  className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                    currentLocale === loc 
                      ? langButtonActiveClass
                      : langButtonInactiveClass
                  }`}
                  aria-label={`Switch to ${loc.toUpperCase()}`}
                >
                  {loc.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Mobile Menu Button */}
            <button
              className={`md:hidden ${textClass} p-2`}
              aria-label="Toggle menu"
            >
              <svg
                className="h-6 w-6"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </nav>

        {/* Mobile Navigation (always visible on mobile for simplicity) */}
        {links && links.length > 0 && (
          <div className={`md:hidden pb-4 border-t border-brand-white/20 pt-4`}>
            <nav className="flex flex-col space-y-3">
              {links.map((link, index) => {
                // Handle both direct object and nested structure from Strapi
                const linkLabel = typeof link === 'object' && link !== null 
                  ? (link.label || (link as any).label)
                  : null;
                const linkHref = typeof link === 'object' && link !== null
                  ? (link.href || (link as any).href)
                  : null;
                const linkIsExternal = typeof link === 'object' && link !== null
                  ? (link.is_external !== undefined ? link.is_external : (link as any).is_external)
                  : false;

                if (!linkLabel || !linkHref) {
                  return null;
                }

                const active = !linkIsExternal && isLinkActive(linkHref);

                return (
                  <Link
                    key={index}
                    href={linkHref}
                    className={`${textClass} ${linkHoverClass} text-sm font-avenir font-medium uppercase tracking-wide transition-colors ${
                      active ? 'border-b border-brand-white pb-1' : ''
                    }`}
                    target={linkIsExternal ? '_blank' : undefined}
                    rel={linkIsExternal ? 'noopener noreferrer' : undefined}
                  >
                    {linkLabel}
                  </Link>
                );
              })}
              
              {/* Mobile CTA Button */}
              {(primary_cta || (cta_label && cta_href)) && (
                <div className="pt-2">
                  {primary_cta ? (
                    primary_cta.is_external ? (
                      <a
                        href={primary_cta.href}
                        className="btn-primary"
                        target="_blank"
                        rel="noreferrer"
                      >
                        {primary_cta.label}
                      </a>
                    ) : (
                      <Link
                        href={primary_cta.href}
                        className="btn-primary"
                      >
                        {primary_cta.label}
                      </Link>
                    )
                  ) : cta_href ? (
                    <Link
                      href={cta_href}
                      className="btn-primary"
                    >
                      {cta_label}
                    </Link>
                  ) : null}
                </div>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}
