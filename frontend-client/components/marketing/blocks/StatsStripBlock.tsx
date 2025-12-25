/**
 * Stats Strip Block - Renders statistics from Strapi CMS
 * Used in Dynamic Zone sections
 */

import { getMediaUrl, StrapiMedia } from '@/lib/cms';

export interface StatItem {
  label: string;
  value: string;
  hint?: string;
  icon?: string;
}

export interface StatsStripBlockProps {
  title?: string;
  items?: StatItem[];
  variant?: 'plain' | 'carded';
}

export function StatsStripBlock({
  title,
  items = [],
  variant = 'carded',
}: StatsStripBlockProps) {
  if (items.length === 0) {
    return null;
  }

  if (variant === 'plain') {
    return (
      <section className="py-12 md:py-16 bg-[#272727]">
        <div className="container mx-auto px-4">
          {title && (
            <h2 className="text-2xl md:text-3xl font-semibold text-center mb-8 text-gray-900">
              {title}
            </h2>
          )}
          <div className="flex flex-wrap items-center justify-center gap-8 md:gap-12">
            {items.map((item, index) => (
              <div key={index} className="text-center">
                <div className="text-3xl md:text-4xl font-bold text-[#fab758] mb-1">
                  {item.value}
                </div>
                <div className="text-sm md:text-base text-gray-700 font-medium">
                  {item.label}
                </div>
                {item.hint && (
                  <div className="text-xs text-gray-500 mt-1">
                    {item.hint}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  // Carded variant
  return (
    <section className="py-16 md:py-24 bg-[#272727]">
      <div className="container mx-auto px-4">
        {title && (
          <h2 className="text-3xl md:text-4xl font-semibold text-center mb-12 text-gray-900">
            {title}
          </h2>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {items.map((item, index) => (
            <div
              key={index}
              className="bg-gray-50 rounded-lg p-6 text-center border border-gray-200 hover:shadow-lg transition-shadow"
            >
              {item.icon && (
                <div className="text-3xl mb-4 text-[#fab758]">
                  {item.icon}
                </div>
              )}
              <div className="text-4xl md:text-5xl font-bold text-gray-900 mb-2">
                {item.value}
              </div>
              <div className="text-lg font-semibold text-gray-700 mb-1">
                {item.label}
              </div>
              {item.hint && (
                <div className="text-sm text-gray-500">
                  {item.hint}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}


