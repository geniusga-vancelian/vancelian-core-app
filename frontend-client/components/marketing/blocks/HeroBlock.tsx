/**
 * Hero Block - Hero section from Strapi CMS
 * Tailwind-only, no external dependencies
 */

'use client';

import Link from 'next/link';
import { getMediaUrl, StrapiMedia } from '@/lib/cms';

export interface HeroCTA {
  label: string;
  href: string;
  is_external?: boolean;
}

export interface HeroBlockProps {
  title: string;
  subtitle?: string;
  description?: string;
  eyebrow?: string;
  background_image?: StrapiMedia;
  primary_cta?: HeroCTA;
  secondary_cta?: HeroCTA;
  align?: 'left' | 'center';
  theme?: 'light' | 'dark';
}

export function HeroBlock({
  title,
  subtitle,
  description,
  eyebrow,
  background_image,
  primary_cta,
  secondary_cta,
  align = 'center',
  theme = 'dark',
}: HeroBlockProps) {
  const backgroundImageUrl = getMediaUrl(background_image);
  const isDark = theme === 'dark';
  const isLeft = align === 'left';

  // DEV ONLY: Debug logging
  if (process.env.NODE_ENV === 'development') {
    console.log('[HeroBlock] Rendering', {
      title,
      hasBackgroundImage: !!background_image,
      backgroundImageUrl,
      backgroundImageData: background_image,
    });
  }

  // Text colors based on theme
  const textClass = isDark ? 'text-white' : 'text-gray-900';
  const eyebrowClass = isDark ? 'text-white/70' : 'text-gray-600';
  const subtitleClass = isDark ? 'text-white/80' : 'text-gray-700';
  const descriptionClass = isDark ? 'text-white/70' : 'text-gray-600';

  // Container alignment
  const containerAlignClass = isLeft ? 'text-left' : 'text-center';
  const contentAlignClass = isLeft ? 'items-start' : 'items-center';

  // Background styles - ensure backgroundImageUrl is valid string
  const hasValidImage = backgroundImageUrl && typeof backgroundImageUrl === 'string' && backgroundImageUrl.length > 0;
  const backgroundStyle = hasValidImage
    ? {
        backgroundImage: `linear-gradient(to bottom, rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.7)), url(${backgroundImageUrl})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }
    : isDark
    ? {
        background: 'linear-gradient(135deg, #1e3a8a 0%, #1e40af 50%, #1e3a8a 100%)',
      }
    : {
        background: 'linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 50%, #d1d5db 100%)',
      };

  // CTA button styles - Both use design system classes
  const primaryButtonClass = 'btn-primary';
  const secondaryButtonClass = isDark 
    ? 'btn-secondary btn-secondary-dark' 
    : 'btn-secondary btn-secondary-light';

  return (
    <section
      className="relative w-full h-[660px] -mt-[96px] md:-mt-[112px] overflow-hidden"
      style={backgroundStyle}
    >
      {/* Background image covers full width from top (starts at pixel 0, behind navbar) */}
      {/* Content container - positioned to be visible under the sticky navbar */}
      <div className="max-w-[1200px] mx-auto px-4 h-full flex items-center pt-[96px] md:pt-[112px]">
        <div className={`flex flex-col ${contentAlignClass} space-y-6 ${containerAlignClass} w-full`}>
          {/* Eyebrow */}
          {eyebrow && (
            <p className={`text-sm md:text-base font-medium uppercase tracking-wider ${eyebrowClass}`}>
              {eyebrow}
            </p>
          )}

          {/* Title */}
          <h1 className={`text-[36px] font-avenir font-light uppercase leading-tight ${textClass}`}>
            {title}
          </h1>

          {/* Subtitle */}
          {subtitle && (
            <p className={`text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 max-w-3xl ${subtitleClass}`}>
              {subtitle}
            </p>
          )}

          {/* Description */}
          {description && (
            <p className={`text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 max-w-3xl ${descriptionClass}`}>
              {description}
            </p>
          )}

          {/* CTAs */}
          {(primary_cta || secondary_cta) && (
            <div className={`flex flex-wrap gap-4 mt-8 ${isLeft ? 'justify-start' : 'justify-center'}`}>
              {primary_cta && (
                <Link
                  href={primary_cta.href}
                  className={primaryButtonClass}
                  target={primary_cta.is_external ? '_blank' : undefined}
                  rel={primary_cta.is_external ? 'noopener noreferrer' : undefined}
                >
                  {primary_cta.label}
                </Link>
              )}
              {secondary_cta && (
                <Link
                  href={secondary_cta.href}
                  className={secondaryButtonClass}
                  target={secondary_cta.is_external ? '_blank' : undefined}
                  rel={secondary_cta.is_external ? 'noopener noreferrer' : undefined}
                >
                  {secondary_cta.label}
                </Link>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
