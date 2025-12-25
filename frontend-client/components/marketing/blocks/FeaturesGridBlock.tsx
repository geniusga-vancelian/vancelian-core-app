/**
 * Features Grid Block - Grid of feature cards organized in rows
 * Similar to Revolut "Switch in 3 Steps" section
 */

'use client';

import Link from 'next/link';
import Image from 'next/image';
import { getMediaUrl, StrapiMedia } from '@/lib/cms';

// Optional Lucide icons - import only if available
let LucideIcons: any = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  LucideIcons = require('lucide-react');
} catch (e) {
  // lucide-react not installed - icons will not be displayed
  if (process.env.NODE_ENV === 'development') {
    console.warn('[FeaturesGridBlock] lucide-react not installed. Install it with: npm install lucide-react');
  }
}

export interface CtaLink {
  label: string;
  href: string;
  is_external?: boolean;
}

export interface FeatureCard {
  eyebrow?: string;
  title: string;
  text: string;
  bullet_type?: 'number' | 'icon';
  bullet_value?: string;
  // Backward compatibility (deprecated, use bullet_value instead)
  number?: number;
  icon?: string;
  card_theme?: 'light' | 'muted' | 'dark';
  accent?: 'none' | 'brand' | 'success' | 'warning' | 'info';
  image?: StrapiMedia;
  cta?: CtaLink;
}

export interface FeaturesRow {
  columns: 'two' | 'three' | 'four';
  cards: FeatureCard[];
}

export interface FeaturesGridBlockProps {
  title: string;
  subtitle?: string;
  cta?: CtaLink;
  rows: FeaturesRow[];
  anchor_id?: string;
}

// Helper to get Lucide icon component by name with fallback
function getLucideIcon(iconName?: string) {
  if (!LucideIcons) {
    // lucide-react not installed - return null
    return null;
  }
  if (!iconName) {
    // Fallback to Sparkles if icon name is missing
    return LucideIcons.Sparkles || null;
  }
  // Convert PascalCase to match Lucide export names
  const IconComponent = LucideIcons[iconName];
  // Fallback to Sparkles if icon not found
  return IconComponent || (LucideIcons.Sparkles || null);
}

// Helper to get accent colors
function getAccentClasses(accent: string = 'brand') {
  switch (accent) {
    case 'success':
      return 'bg-green-500 text-white';
    case 'warning':
      return 'bg-yellow-500 text-white';
    case 'info':
      return 'bg-blue-500 text-white';
    case 'none':
      return 'bg-gray-400 text-white';
    case 'brand':
    default:
      return 'bg-neutral-900 text-white';
  }
}

// Helper to get card theme classes
function getCardThemeClasses(theme: string = 'muted') {
  switch (theme) {
    case 'light':
      return 'bg-white border border-gray-200 text-gray-900';
    case 'dark':
      return 'bg-gray-900 text-white border border-gray-800';
    case 'muted':
    default:
      return 'bg-gray-50 text-gray-900 border border-gray-100';
  }
}

// Helper to get grid columns classes
function getGridColsClass(columns: string) {
  switch (columns) {
    case 'two':
      return 'md:grid-cols-2';
    case 'four':
      return 'md:grid-cols-2 lg:grid-cols-4';
    case 'three':
    default:
      return 'md:grid-cols-3';
  }
}

export function FeaturesGridBlock({
  title,
  subtitle,
  cta,
  rows,
  anchor_id,
}: FeaturesGridBlockProps) {
  if (!rows || rows.length === 0) {
    return null;
  }

  // Section CTA Link component
  const sectionCtaLink = cta && (
    cta.is_external ? (
      <a
        href={cta.href}
        className="inline-flex items-center justify-center rounded-full bg-neutral-900 px-6 py-3 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
        target="_blank"
        rel="noreferrer"
      >
        {cta.label}
      </a>
    ) : (
      <Link
        href={cta.href}
        className="inline-flex items-center justify-center rounded-full bg-neutral-900 px-6 py-3 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
      >
        {cta.label}
      </Link>
    )
  );

  // Card CTA Link component
  const CardCtaLink = ({ cardCta }: { cardCta: CtaLink }) => {
    const linkClass = 'mt-4 inline-flex items-center justify-center rounded-full bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity';
    
    return cardCta.is_external ? (
      <a
        href={cardCta.href}
        className={linkClass}
        target="_blank"
        rel="noreferrer"
      >
        {cardCta.label}
      </a>
    ) : (
      <Link href={cardCta.href} className={linkClass}>
        {cardCta.label}
      </Link>
    );
  };

  const sectionProps: { id?: string; className: string } = {
    className: 'py-16 md:py-24 bg-[#272727]',
  };

  if (anchor_id) {
    sectionProps.id = anchor_id;
  }

  return (
    <section {...sectionProps}>
      <div className="mx-auto max-w-7xl px-4 md:px-6">
        {/* Section Header */}
        <div className="text-center mb-12">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
            <div className="flex-1">
              <h2 className="text-[36px] font-avenir font-light uppercase text-gray-900">
                {title}
              </h2>
              {subtitle && (
                <p className="text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 text-neutral-500">
                  {subtitle}
                </p>
              )}
            </div>
            {sectionCtaLink && (
              <div className="flex justify-center md:justify-end">
                {sectionCtaLink}
              </div>
            )}
          </div>
        </div>

        {/* Rows */}
        <div className="space-y-8 md:space-y-12">
          {rows.map((row, rowIndex) => (
            <div
              key={rowIndex}
              className={`grid grid-cols-1 ${getGridColsClass(row.columns)} gap-6 md:gap-8`}
            >
              {row.cards.map((card, cardIndex) => {
                // Backward compatibility: merge bullet_value with old number/icon fields
                const bulletValue = card.bullet_value ?? 
                  (card.bullet_type === 'number' ? String(card.number ?? '') : card.icon ?? '');

                // Determine if we should render a bullet
                const isNumberType = card.bullet_type === 'number';
                const isIconType = card.bullet_type === 'icon';
                
                // For number type: use bullet_value, or auto-generate from index if missing
                const numberValue = isNumberType 
                  ? (bulletValue || String(cardIndex + 1))
                  : null;
                
                // For icon type: use bullet_value to get icon component
                const IconComponent = isIconType && bulletValue ? getLucideIcon(bulletValue) : null;
                
                const themeClasses = getCardThemeClasses(card.card_theme);
                const accentClasses = getAccentClasses(card.accent);
                const imageUrl = card.image ? getMediaUrl(card.image) : null;
                const isDark = card.card_theme === 'dark';

                // Render bullet if we have a number or icon
                const shouldRenderBullet = (isNumberType && numberValue) || (isIconType && IconComponent);

                return (
                  <div
                    key={cardIndex}
                    className={`rounded-2xl ${themeClasses} p-6 md:p-8 flex flex-col h-full`}
                  >
                    {/* Bullet (Number or Icon) */}
                    {shouldRenderBullet ? (
                      <div className="mb-4">
                        {isNumberType && numberValue ? (
                          <div className={`w-10 h-10 rounded-full ${accentClasses} flex items-center justify-center text-lg font-bold`}>
                            {numberValue}
                          </div>
                        ) : IconComponent ? (
                          <div className={`w-10 h-10 rounded-full ${accentClasses} flex items-center justify-center`}>
                            <IconComponent className="w-5 h-5" />
                          </div>
                        ) : null}
                      </div>
                    ) : null}

                    {/* Eyebrow (optional) */}
                    {card.eyebrow && (
                      <div className="mb-2">
                        <span className={`text-xs font-medium uppercase tracking-wide ${
                          isDark ? 'text-white/70' : 'text-gray-500'
                        }`}>
                          {card.eyebrow}
                        </span>
                      </div>
                    )}

                    {/* Title */}
                    <h3 className={`text-[36px] font-avenir font-light uppercase mb-3 ${
                      isDark ? 'text-white' : 'text-gray-900'
                    }`}>
                      {card.title}
                    </h3>

                    {/* Text */}
                    <p className={`flex-1 text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 ${
                      isDark ? 'text-white/80' : 'text-gray-600'
                    }`}>
                      {card.text}
                    </p>

                    {/* Card CTA (optional) */}
                    {card.cta && (
                      <div className="mt-4">
                        <CardCtaLink cardCta={card.cta} />
                      </div>
                    )}

                    {/* Image (optional) */}
                    {imageUrl && (
                      <div className="mt-6 -mx-6 md:-mx-8 -mb-6 md:-mb-8">
                        <div className="relative w-full aspect-video rounded-b-2xl overflow-hidden">
                          <Image
                            src={imageUrl}
                            alt={card.title}
                            fill
                            className="object-contain object-center"
                            sizes="(max-width: 768px) 100vw, 33vw"
                            unoptimized={imageUrl.includes('localhost:1337')}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
