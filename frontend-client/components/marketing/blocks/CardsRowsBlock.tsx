/**
 * Cards Rows Block - Section with multiple rows of hero cards
 * Each row can contain 1 or 2 cards with different layouts
 */

'use client';

import { HeroCard } from './HeroCard';

export interface HeroCardData {
  eyebrow?: string;
  title?: string;
  description?: string;
  background_image?: any;
  text_position?: string;
  cta?: {
    label: string;
    href: string;
    is_external?: boolean;
  };
}

export interface CardsRowData {
  layout: 'one-full' | 'two-50-50' | 'two-60-40' | 'two-40-60' | 'two-70-30' | 'two-30-70' | 'two-75-25' | 'two-25-75';
  cards: HeroCardData[];
  gap?: number;
}

export interface CardsRowsBlockProps {
  title?: string;
  subtitle?: string;
  rows?: CardsRowData[];
  anchor_id?: string;
}

export function CardsRowsBlock({
  title,
  subtitle,
  rows = [],
  anchor_id,
}: CardsRowsBlockProps) {
  if (!rows || rows.length === 0) {
    return null;
  }

  // Get grid classes based on layout
  const getGridClasses = (layout: string, gap: number = 24) => {
    // Convert gap to Tailwind gap class (gap is in pixels)
    const gapClass = gap === 24 ? 'gap-6' : gap === 16 ? 'gap-4' : gap === 32 ? 'gap-8' : `gap-[${gap}px]`;
    
    // Base: always grid with 1 column on mobile
    const baseClasses = `grid grid-cols-1 ${gapClass}`;

    switch (layout) {
      case 'one-full':
        return `${baseClasses} md:grid-cols-1`;
      case 'two-50-50':
        return `${baseClasses} md:grid-cols-2`;
      case 'two-60-40':
        return `${baseClasses} md:grid-cols-5`;
      case 'two-40-60':
        return `${baseClasses} md:grid-cols-5`;
      case 'two-70-30':
        return `${baseClasses} md:grid-cols-10`;
      case 'two-30-70':
        return `${baseClasses} md:grid-cols-10`;
      case 'two-75-25':
        return `${baseClasses} md:grid-cols-4`;
      case 'two-25-75':
        return `${baseClasses} md:grid-cols-4`;
      // Backward compatibility with old layouts
      case 'two-equal':
        return `${baseClasses} md:grid-cols-2`;
      case 'two-2-3':
        return `${baseClasses} md:grid-cols-5`;
      case 'two-1-3':
        return `${baseClasses} md:grid-cols-4`;
      default:
        return `${baseClasses} md:grid-cols-2`;
    }
  };

  // Get card span classes for asymmetric layouts
  const getCardSpanClasses = (layout: string, index: number) => {
    switch (layout) {
      case 'two-60-40':
        return index === 0 ? 'md:col-span-3' : 'md:col-span-2';
      case 'two-40-60':
        return index === 0 ? 'md:col-span-2' : 'md:col-span-3';
      case 'two-70-30':
        return index === 0 ? 'md:col-span-7' : 'md:col-span-3';
      case 'two-30-70':
        return index === 0 ? 'md:col-span-3' : 'md:col-span-7';
      case 'two-75-25':
        return index === 0 ? 'md:col-span-3' : 'md:col-span-1';
      case 'two-25-75':
        return index === 0 ? 'md:col-span-1' : 'md:col-span-3';
      // Backward compatibility
      case 'two-2-3':
        return index === 0 ? 'md:col-span-3' : 'md:col-span-2';
      case 'two-1-3':
        return index === 0 ? 'md:col-span-1' : 'md:col-span-3';
      default:
        return '';
    }
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
        {(title || subtitle) && (
          <div className="text-center mb-12">
            {title && (
              <h2 className="text-[36px] font-avenir font-light uppercase text-gray-900">
                {title}
              </h2>
            )}
            {subtitle && (
              <p className="mt-3 text-base md:text-lg text-neutral-500">
                {subtitle}
              </p>
            )}
          </div>
        )}

        {/* Rows */}
        <div className="space-y-6 md:space-y-8">
          {rows.map((row, rowIndex) => {
            // Validation: if layout starts with 'two-' but only 1 card, fallback to one-full
            let effectiveLayout = row.layout;
            if (row.layout?.startsWith('two-') && (!row.cards || row.cards.length === 1)) {
              if (process.env.NODE_ENV === 'development') {
                console.warn(`[CardsRowsBlock] Layout '${row.layout}' requires 2 cards, but only 1 provided. Falling back to one-full.`);
              }
              effectiveLayout = 'one-full';
            }
            // If layout is one-full but 2 cards, render only the first one
            if (effectiveLayout === 'one-full' && row.cards && row.cards.length > 1) {
              if (process.env.NODE_ENV === 'development') {
                console.warn(`[CardsRowsBlock] Layout 'one-full' can only display 1 card, but ${row.cards.length} provided. Rendering first card only.`);
              }
            }

            const cardsToRender = effectiveLayout === 'one-full' && row.cards && row.cards.length > 1
              ? [row.cards[0]]
              : row.cards || [];

            return (
              <div
                key={rowIndex}
                className={getGridClasses(effectiveLayout, row.gap)}
              >
                {cardsToRender.map((card, cardIndex) => (
                  <div
                    key={cardIndex}
                    className={getCardSpanClasses(effectiveLayout, cardIndex)}
                  >
                    <HeroCard
                      eyebrow={card.eyebrow}
                      title={card.title}
                      description={card.description}
                      background_image={card.background_image}
                      text_position={card.text_position as any}
                      cta={card.cta}
                    />
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
