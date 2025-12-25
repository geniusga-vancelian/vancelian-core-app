/**
 * Partners Strip Block - Displays partner logos in a grid or carousel
 * Tailwind CSS only, no external dependencies
 */

'use client';

import Image from 'next/image';
import Link from 'next/link';
import { getMediaUrl, StrapiMedia } from '@/lib/cms';

export interface PartnerLogo {
  id?: number;
  name: string;
  type?: 'media' | 'financial' | 'technology';
  logo: StrapiMedia;
  url?: string;
  order?: number;
  is_featured?: boolean;
}

export interface PartnersStripBlockProps {
  title?: string;
  subtitle?: string;
  partner_kind?: 'all' | 'media' | 'financial' | 'technology';
  layout?: 'grid' | 'carousel';
  theme?: 'light' | 'dark';
  show_names?: boolean;
  grayscale?: boolean;
  logos?: PartnerLogo[];
}

export function PartnersStripBlock({
  title,
  subtitle,
  partner_kind = 'all',
  layout = 'grid',
  theme = 'light',
  show_names = false,
  grayscale = true,
  logos = [],
}: PartnersStripBlockProps) {
  // DEV ONLY: Debug logging
  if (process.env.NODE_ENV === 'development') {
    console.log('[PartnersStripBlock] Rendering', {
      title,
      subtitle,
      logosCount: logos.length,
      logos: logos.map(logo => ({
        name: logo.name,
        hasLogo: !!logo.logo,
        logoData: logo.logo,
      })),
    });
  }

  // Filter logos by partner_kind if needed
  const filteredLogos = partner_kind === 'all'
    ? logos
    : logos.filter(logo => logo.type === partner_kind);

  // Sort by order if available
  const sortedLogos = [...filteredLogos].sort((a, b) => (a.order || 0) - (b.order || 0));

  const isDark = theme === 'dark';
  const bgClass = isDark ? 'bg-gray-900' : 'bg-[#272727]';
  const textClass = isDark ? 'text-white' : 'text-gray-900';
  const subtitleClass = isDark ? 'text-white/80' : 'text-gray-600';

  // Grayscale filter class
  const grayscaleClass = grayscale ? 'grayscale hover:grayscale-0 transition-all duration-300' : '';

  // Calculate responsive grid columns based on number of logos
  // Using tighter gaps for a more compact, tassé layout like the example
  const logoCount = sortedLogos.length;
  const getGridColsClass = () => {
    if (layout === 'carousel') {
      return 'flex overflow-x-auto snap-x snap-mandatory scrollbar-hide space-x-6 pb-4';
    }

    // Responsive grid columns based on logo count
    // Using smaller gaps (gap-6 instead of gap-8) for a more compact layout
    // Mobile (default): max 2 columns
    // Tablet (md): adapt based on count (max 3-4)
    // Desktop (lg): adapt based on count (max 6)
    
    if (logoCount === 1) {
      return 'grid grid-cols-1 gap-6';
    } else if (logoCount === 2) {
      return 'grid grid-cols-2 gap-6';
    } else if (logoCount === 3) {
      return 'grid grid-cols-2 md:grid-cols-3 gap-6';
    } else if (logoCount === 4) {
      return 'grid grid-cols-2 md:grid-cols-4 gap-6';
    } else if (logoCount === 5) {
      return 'grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6';
    } else {
      // 6 or more logos: use responsive grid up to 6 columns
      return 'grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6';
    }
  };

  const containerClass = getGridColsClass();

  if (sortedLogos.length === 0) {
    return null;
  }

  return (
    <section className={`py-12 md:py-16 ${bgClass}`}>
      <div className="max-w-[1200px] mx-auto px-4">
        {/* Title and Subtitle */}
        {(title || subtitle) && (
          <div className="text-center mb-8 md:mb-10">
            {title && (
              <h2 className={`text-[36px] font-avenir font-light uppercase mb-3 ${textClass}`}>
                {title}
              </h2>
            )}
            {subtitle && (
              <p className={`text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 ${subtitleClass}`}>
                {subtitle}
              </p>
            )}
          </div>
        )}

        {/* Logos Container */}
        <div className={containerClass}>
          {sortedLogos.map((logo, index) => {
            const logoUrl = getMediaUrl(logo.logo);
            
            // DEV ONLY: Debug logging for each logo
            if (process.env.NODE_ENV === 'development') {
              if (!logoUrl) {
                console.warn('[PartnersStripBlock] Logo URL is null for:', {
                  name: logo.name,
                  logoData: logo.logo,
                });
              } else {
                console.log('[PartnersStripBlock] Logo URL for', logo.name, ':', logoUrl);
              }
            }
            
            if (!logoUrl) return null;

            const logoContent = (
              <div
                key={logo.id || index}
                className={`flex items-center justify-center ${
                  layout === 'grid' ? 'snap-center' : ''
                } ${logo.is_featured ? 'opacity-100' : 'opacity-70 hover:opacity-100'} transition-opacity`}
              >
                {/* Fixed height container for consistent logo heights - max 50px */}
                <div className={`relative w-full h-10 md:h-12 lg:h-[50px] ${grayscaleClass}`}>
                  <Image
                    src={logoUrl}
                    alt={logo.name || `Partner ${index + 1}`}
                    fill
                    className="object-contain object-center"
                    sizes="(max-width: 768px) 50vw, (max-width: 1024px) 25vw, 16vw"
                    unoptimized={logoUrl.includes('localhost:1337')}
                  />
                </div>
                {show_names && logo.name && (
                  <p className={`mt-2 text-xs font-medium ${textClass}`}>
                    {logo.name}
                  </p>
                )}
              </div>
            );

            // Wrap in link if URL provided
            if (logo.url) {
              return (
                <Link
                  key={logo.id || index}
                  href={logo.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block"
                >
                  {logoContent}
                </Link>
              );
            }

            return logoContent;
          })}
        </div>
      </div>
    </section>
  );
}

