/**
 * Ambassador Section Block - Displays partnership/ambassador section
 * Big rounded hero card with optional background image and overlay
 */

'use client';

import Link from 'next/link';
import { getMediaUrl, StrapiMedia } from '@/lib/cms';

export interface CtaLink {
  label: string;
  href: string;
  is_external?: boolean;
}

export interface AmbassadorSectionBlockProps {
  title?: string;
  subtitle?: string;
  card_title?: string;
  card_text?: string;
  cta?: CtaLink;
  background_image?: StrapiMedia;
  overlay_opacity?: number;
  card_height?: 'md' | 'lg' | 'xl';
  content_max_width?: 'sm' | 'md' | 'lg';
  align?: 'left' | 'center';
  anchor_id?: string;
}

export function AmbassadorSectionBlock({
  title,
  subtitle,
  card_title,
  card_text,
  cta,
  background_image,
  overlay_opacity,
  card_height = 'lg',
  content_max_width = 'md',
  align = 'left',
  anchor_id,
}: AmbassadorSectionBlockProps) {
  // DEV ONLY: Debug logging
  if (process.env.NODE_ENV === 'development') {
    console.log('[AmbassadorSectionBlock] Rendering with props', {
      title,
      subtitle,
      card_title,
      card_text,
      cta,
      hasBackgroundImage: !!background_image,
      overlay_opacity,
      card_height,
      content_max_width,
      align,
    });
  }

  // Validate required fields
  if (!title || !subtitle || !card_title || !card_text || !cta) {
    if (process.env.NODE_ENV === 'development') {
      console.warn('[AmbassadorSectionBlock] Missing required fields', {
        hasTitle: !!title,
        hasSubtitle: !!subtitle,
        hasCardTitle: !!card_title,
        hasCardText: !!card_text,
        hasCta: !!cta,
      });
    }
    return null;
  }

  // Get background image URL
  const bgUrl = getMediaUrl(background_image);

  // Handle overlay opacity: if 0-85 (int) convert to 0-0.85, if 0-1 use directly
  const overlayValue = overlay_opacity !== undefined ? overlay_opacity : 35;
  const overlay = overlayValue > 1 ? overlayValue / 100 : overlayValue;

  // Card height classes
  const heightClasses = {
    md: 'min-h-[340px]',
    lg: 'min-h-[420px]',
    xl: 'min-h-[520px]',
  };

  // Content max width classes
  const contentMaxWidthClasses = {
    sm: 'max-w-[360px]',
    md: 'max-w-[420px]',
    lg: 'max-w-[520px]',
  };

  const heightClass = heightClasses[card_height];
  const contentMaxWidthClass = contentMaxWidthClasses[content_max_width];
  const isCenter = align === 'center';

  // CTA Link component
  const ctaLink = cta.is_external ? (
    <a
      href={cta.href}
      className="mt-8 inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-semibold text-neutral-900 hover:opacity-95 transition-opacity"
      target="_blank"
      rel="noreferrer"
    >
      {cta.label}
    </a>
  ) : (
    <Link
      href={cta.href}
      className="mt-8 inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-semibold text-neutral-900 hover:opacity-95 transition-opacity"
    >
      {cta.label}
    </Link>
  );

  const sectionProps: { id?: string; className: string } = {
    className: 'py-16 md:py-24 bg-[#272727]',
  };

  if (anchor_id) {
    sectionProps.id = anchor_id;
  }

  return (
    <section {...sectionProps}>
      <div className="mx-auto max-w-6xl px-4 md:px-6">
        {/* Section Header */}
        <div className="text-center mb-10">
          <h2 className="text-[36px] font-avenir font-light uppercase text-gray-900">
            {title}
          </h2>
          <p className="text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 text-neutral-500">
            {subtitle}
          </p>
        </div>

        {/* Card */}
        <div className="relative overflow-hidden rounded-[32px] shadow-sm">
          {/* Background Image */}
          {bgUrl ? (
            <div className="absolute inset-0">
              <img
                src={bgUrl}
                alt=""
                className="h-full w-full object-cover object-center"
                loading="lazy"
              />
              <div
                className="absolute inset-0"
                style={{ backgroundColor: `rgba(0, 0, 0, ${overlay})` }}
              />
            </div>
          ) : (
            // Fallback gradient background when no image
            <div className="absolute inset-0 bg-gradient-to-br from-neutral-900 via-neutral-800 to-neutral-900" />
          )}

          {/* Content */}
          <div
            className={`relative z-10 px-6 md:px-10 py-12 md:py-16 flex items-center ${heightClass} ${
              isCenter ? 'justify-center' : 'justify-start'
            }`}
          >
            <div className={`text-white ${contentMaxWidthClass} ${isCenter ? 'text-center' : 'text-left'}`}>
              <h3 className="text-[36px] font-avenir font-light uppercase leading-tight">
                {card_title}
              </h3>
              <p className="text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 text-white/85">
                {card_text}
              </p>
              <div className={isCenter ? 'flex justify-center' : ''}>
                {ctaLink}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

