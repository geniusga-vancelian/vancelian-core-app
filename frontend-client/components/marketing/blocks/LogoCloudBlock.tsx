/**
 * Logo Cloud Block - Renders logos from Strapi CMS
 * Used in Dynamic Zone sections
 */

'use client';

import { getMediaUrl, StrapiMedia } from '@/lib/cms';
import { getStrapiBaseUrl } from '@/lib/config';

export interface LogoItem {
  name: string;
  logo: StrapiMedia;
  href?: string;
  dark_logo?: StrapiMedia;
}

export interface LogoCloudBlockProps {
  title?: string;
  items?: LogoItem[];
  variant?: 'grid' | 'carousel';
}

function getLogoUrl(media: StrapiMedia | undefined): string | null {
  if (!media) return null;
  const url = getMediaUrl(media);
  if (!url) return null;
  // Ensure absolute URL
  if (url.startsWith('http')) return url;
  const baseUrl = getStrapiBaseUrl().replace('/api', '');
  return `${baseUrl}${url.startsWith('/') ? url : `/${url}`}`;
}

export function LogoCloudBlock({
  title,
  items = [],
  variant = 'grid',
}: LogoCloudBlockProps) {
  if (items.length === 0) {
    return null;
  }

  if (variant === 'carousel') {
    return (
      <section className="py-12 md:py-16 bg-[#272727]">
        <div className="container mx-auto px-4">
          {title && (
            <h2 className="text-2xl md:text-3xl font-semibold text-center mb-8 text-gray-900">
              {title}
            </h2>
          )}
          <div className="overflow-x-auto">
            <div className="flex items-center gap-8 md:gap-12 min-w-max px-4">
              {items.map((item, index) => {
                const logoUrl = getLogoUrl(item.logo);
                if (!logoUrl) return null;

                const content = (
                  <div className="flex items-center justify-center h-16 w-32 md:h-20 md:w-40 grayscale hover:grayscale-0 transition-all duration-300 opacity-60 hover:opacity-100">
                    <img
                      src={logoUrl}
                      alt={item.name}
                      className="max-h-full max-w-full object-contain"
                    />
                  </div>
                );

                if (item.href) {
                  return (
                    <a
                      key={index}
                      href={item.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block"
                    >
                      {content}
                    </a>
                  );
                }

                return <div key={index}>{content}</div>;
              })}
            </div>
          </div>
        </div>
      </section>
    );
  }

  // Grid variant
  return (
    <section className="py-16 md:py-24 bg-[#272727]">
      <div className="container mx-auto px-4">
        {title && (
          <h2 className="text-3xl md:text-4xl font-semibold text-center mb-12 text-gray-900">
            {title}
          </h2>
        )}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-8 items-center max-w-6xl mx-auto">
          {items.map((item, index) => {
            const logoUrl = getLogoUrl(item.logo);
            if (!logoUrl) return null;

            const content = (
              <div className="flex items-center justify-center h-16 md:h-20 grayscale hover:grayscale-0 transition-all duration-300 opacity-60 hover:opacity-100">
                <img
                  src={logoUrl}
                  alt={item.name}
                  className="max-h-full max-w-full object-contain"
                />
              </div>
            );

            if (item.href) {
              return (
                <a
                  key={index}
                  href={item.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block"
                >
                  {content}
                </a>
              );
            }

            return <div key={index}>{content}</div>;
          })}
        </div>
      </div>
    </section>
  );
}

