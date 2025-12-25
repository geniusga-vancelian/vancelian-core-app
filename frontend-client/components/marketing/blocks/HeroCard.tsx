/**
 * Hero Card - Reusable card component with background image, overlay, and text
 * Used by CardsRowsBlock and AmbassadorSectionBlock
 */

'use client';

import Link from 'next/link';
import Image from 'next/image';
import { getMediaUrl, StrapiMedia } from '@/lib/cms';

export interface CtaLink {
  label: string;
  href: string;
  is_external?: boolean;
}

export interface HeroCardProps {
  eyebrow?: string;
  title?: string;
  description?: string;
  background_image?: StrapiMedia;
  text_position?: 'top-left' | 'center-left' | 'bottom-left' | 'top-center' | 'center-center' | 'bottom-center' | 'top-right' | 'center-right' | 'bottom-right';
  cta?: CtaLink;
  className?: string;
}

export function HeroCard({
  eyebrow,
  title,
  description,
  background_image,
  text_position = 'center-left',
  cta,
  className = '',
}: HeroCardProps) {
  if (!title || !description || !background_image) {
    return null;
  }

  const bgUrl = getMediaUrl(background_image);
  if (!bgUrl) {
    return null;
  }

  // Text position classes for flex container (outer container positioning)
  const positionClasses = {
    'top-left': 'justify-start items-start',
    'center-left': 'justify-start items-center',
    'bottom-left': 'justify-start items-end',
    'top-center': 'justify-center items-start',
    'center-center': 'justify-center items-center',
    'bottom-center': 'justify-center items-end',
    'top-right': 'justify-end items-start',
    'center-right': 'justify-end items-center',
    'bottom-right': 'justify-end items-end',
  };

  // Text alignment class based on horizontal position (for text content alignment)
  const getTextAlignClass = (position: string) => {
    if (position.includes('center')) return 'text-center';
    if (position.includes('right')) return 'text-right';
    return 'text-left';
  };

  const positionClass = positionClasses[text_position] || positionClasses['center-left'];
  const textAlignClass = getTextAlignClass(text_position);

  // CTA Link component
  const ctaLink = cta && (
    cta.is_external ? (
      <a
        href={cta.href}
        className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-semibold text-neutral-900 hover:opacity-95 transition-opacity"
        target="_blank"
        rel="noreferrer"
      >
        {cta.label}
      </a>
    ) : (
      <Link
        href={cta.href}
        className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-semibold text-neutral-900 hover:opacity-95 transition-opacity"
      >
        {cta.label}
      </Link>
    )
  );

  return (
    <div className={`relative overflow-hidden rounded-[32px] shadow-sm min-h-[420px] ${className}`}>
      {/* Background Image */}
      <div className="absolute inset-0">
        <Image
          src={bgUrl}
          alt={title || ''}
          fill
          className="object-cover object-center"
          sizes="(max-width: 768px) 100vw, 50vw"
          unoptimized={bgUrl.includes('localhost:1337')}
        />
        {/* Dark overlay for readability - similar to ambassador section */}
        <div className="absolute inset-0 bg-gradient-to-br from-black/40 via-black/30 to-black/40" />
      </div>

      {/* Content */}
      <div className={`relative z-10 h-full min-h-[420px] flex px-6 md:px-10 py-12 md:py-16 ${positionClass}`}>
        <div className={`text-white flex flex-col ${textAlignClass} w-full`}>
          {/* Eyebrow (optional) */}
          {eyebrow && (
            <div className="mb-4">
              <span className="inline-block text-sm font-medium text-white/90">
                {eyebrow}
              </span>
            </div>
          )}

          {/* Title */}
          <h3 className="text-[36px] font-avenir font-light uppercase leading-tight">
            {title}
          </h3>

          {/* Description */}
          <p className="text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 text-white/85">
            {description}
          </p>

          {/* CTA (optional) */}
          {ctaLink && (
            <div className={`mt-6 ${textAlignClass === 'text-center' ? 'flex justify-center' : textAlignClass === 'text-right' ? 'flex justify-end' : 'flex justify-start'}`}>
              {ctaLink}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

