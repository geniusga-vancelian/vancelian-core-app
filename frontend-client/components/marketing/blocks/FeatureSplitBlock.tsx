/**
 * Feature Split Block - Text and image split section
 * Image can be on left or right, with optional eyebrow, title, description, and CTA
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

export interface FeatureSplitBlockProps {
  eyebrow?: string;
  eyebrow_variant?: 'neutral' | 'green' | 'purple';
  title?: string;
  description?: string;
  media?: StrapiMedia;
  layout?: 'image_right' | 'image_left';
  cta?: CtaLink;
  anchor_id?: string;
}

export function FeatureSplitBlock({
  eyebrow,
  eyebrow_variant = 'neutral',
  title,
  description,
  media,
  layout = 'image_right',
  cta,
  anchor_id,
}: FeatureSplitBlockProps) {
  if (!title || !description || !media) {
    return null;
  }

  const imageUrl = getMediaUrl(media);
  if (!imageUrl) {
    return null;
  }

  const isImageLeft = layout === 'image_left';
  const isImageRight = layout === 'image_right';

  // Eyebrow color classes
  const eyebrowClasses = {
    neutral: 'bg-neutral-200 text-neutral-800',
    green: 'bg-green-600 text-white',
    purple: 'bg-[#9747FF] text-white',
  };

  // CTA Link component
  const ctaLink = cta && (
    cta.is_external ? (
      <a
        href={cta.href}
        className="mt-8 inline-flex items-center justify-center rounded-full bg-neutral-900 px-6 py-3 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
        target="_blank"
        rel="noreferrer"
      >
        {cta.label}
      </a>
    ) : (
      <Link
        href={cta.href}
        className="mt-8 inline-flex items-center justify-center rounded-full bg-neutral-900 px-6 py-3 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
      >
        {cta.label}
      </Link>
    )
  );

  const sectionProps: { id?: string; className: string } = {
    className: 'py-16 md:py-24 bg-[#272727]',
  };

  if (anchor_id) {
    sectionProps.id = anchor_id;
  }

  // Split title by \n for line breaks
  const titleLines = title.split('\n');

  return (
    <section {...sectionProps}>
      <div className="mx-auto max-w-7xl px-4 md:px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
          {/* Content - toujours en premier dans le HTML, order contrôle l'affichage */}
          <div className={`flex flex-col justify-center ${
            isImageLeft ? 'lg:order-2' : 'lg:order-1'
          }`}>
            {/* Eyebrow (optional) */}
            {eyebrow && (
              <div className="mb-4">
                <span className={`inline-block text-sm font-medium rounded-full px-4 py-1 ${eyebrowClasses[eyebrow_variant]}`}>
                  {eyebrow}
                </span>
              </div>
            )}

            {/* Title */}
            <h2 className="text-[36px] font-avenir font-light uppercase leading-tight text-gray-900">
              {titleLines.map((line, index) => (
                <span key={index}>
                  {line}
                  {index < titleLines.length - 1 && <br />}
                </span>
              ))}
            </h2>

            {/* Description */}
            <p className="text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 text-neutral-700">
              {description}
            </p>

            {/* CTA (optional) */}
            {ctaLink}
          </div>

          {/* Image */}
          <div className={`relative w-full aspect-[4/3] rounded-3xl overflow-hidden ${
            isImageLeft ? 'lg:order-1' : 'lg:order-2'
          }`}>
            <Image
              src={imageUrl}
              alt={title || 'Feature image'}
              fill
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 50vw"
              unoptimized={imageUrl.includes('localhost:1337')}
            />
          </div>
        </div>
      </div>
    </section>
  );
}

