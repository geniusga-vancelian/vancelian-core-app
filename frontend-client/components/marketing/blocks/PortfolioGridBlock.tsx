/**
 * Portfolio Grid Block - Renders portfolio items from Strapi CMS
 * Used in Dynamic Zone sections
 */

'use client';

import { useState, useMemo } from 'react';
import { getMediaUrl, StrapiMedia } from '@/lib/cms';
import { getStrapiBaseUrl } from '@/lib/config';

export interface PortfolioItem {
  title: string;
  subtitle?: string;
  cover_image: StrapiMedia;
  href?: string;
  tags?: string[] | string;
  location?: string;
  year?: string;
}

export interface PortfolioGridBlockProps {
  title?: string;
  subtitle?: string;
  items?: PortfolioItem[];
  columns?: '2' | '3' | '4';
  show_filters?: boolean;
}

function getImageUrl(media: StrapiMedia): string | null {
  const url = getMediaUrl(media);
  if (!url) return null;
  if (url.startsWith('http')) return url;
  const baseUrl = getStrapiBaseUrl().replace('/api', '');
  return `${baseUrl}${url.startsWith('/') ? url : `/${url}`}`;
}

function parseTags(tags: string[] | string | undefined): string[] {
  if (!tags) return [];
  if (Array.isArray(tags)) return tags;
  if (typeof tags === 'string') {
    try {
      const parsed = JSON.parse(tags);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return tags.split(',').map(t => t.trim()).filter(Boolean);
    }
  }
  return [];
}

export function PortfolioGridBlock({
  title,
  subtitle,
  items = [],
  columns = '3',
  show_filters = false,
}: PortfolioGridBlockProps) {
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  // Extract all unique tags
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    items.forEach(item => {
      const tags = parseTags(item.tags);
      tags.forEach(tag => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }, [items]);

  // Filter items by selected tag
  const filteredItems = useMemo(() => {
    if (!selectedTag) return items;
    return items.filter(item => {
      const tags = parseTags(item.tags);
      return tags.includes(selectedTag);
    });
  }, [items, selectedTag]);

  if (items.length === 0) {
    return null;
  }

  const gridCols = {
    '2': 'grid-cols-1 md:grid-cols-2',
    '3': 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    '4': 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
  }[columns];

  return (
    <section className="py-16 md:py-24 bg-[#272727]">
      <div className="container mx-auto px-4">
        {title && (
          <h2 className="text-3xl md:text-4xl font-semibold text-center mb-4 text-gray-900">
            {title}
          </h2>
        )}
        {subtitle && (
          <p className="text-center text-gray-600 mb-12 max-w-2xl mx-auto">
            {subtitle}
          </p>
        )}

        {show_filters && allTags.length > 0 && (
          <div className="flex flex-wrap items-center justify-center gap-2 mb-8">
            <button
              onClick={() => setSelectedTag(null)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                selectedTag === null
                  ? 'bg-[#fab758] text-gray-900'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All
            </button>
            {allTags.map((tag) => (
              <button
                key={tag}
                onClick={() => setSelectedTag(tag)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  selectedTag === tag
                    ? 'bg-[#fab758] text-gray-900'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        )}

        <div className={`grid ${gridCols} gap-6 max-w-6xl mx-auto`}>
          {filteredItems.map((item, index) => {
            const imageUrl = getImageUrl(item.cover_image);
            const tags = parseTags(item.tags);
            
            const cardContent = (
              <div className="group relative overflow-hidden rounded-lg border border-gray-200 hover:shadow-xl transition-shadow">
                {imageUrl && (
                  <div className="aspect-video bg-gray-200 overflow-hidden">
                    <img
                      src={imageUrl}
                      alt={item.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  </div>
                )}
                <div className="p-6">
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    {item.title}
                  </h3>
                  {item.subtitle && (
                    <p className="text-gray-600 mb-3">
                      {item.subtitle}
                    </p>
                  )}
                  <div className="flex flex-wrap items-center gap-2 text-sm text-gray-500">
                    {item.location && (
                      <span className="flex items-center gap-1">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        {item.location}
                      </span>
                    )}
                    {item.year && (
                      <span>{item.year}</span>
                    )}
                  </div>
                  {tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {tags.map((tag, tagIndex) => (
                        <span
                          key={tagIndex}
                          className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );

            if (item.href) {
              const isExternal = item.href.startsWith('http');
              if (isExternal) {
                return (
                  <a
                    key={index}
                    href={item.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block"
                  >
                    {cardContent}
                  </a>
                );
              }
              return (
                <a key={index} href={item.href} className="block">
                  {cardContent}
                </a>
              );
            }

            return <div key={index}>{cardContent}</div>;
          })}
        </div>

        {show_filters && filteredItems.length === 0 && (
          <p className="text-center text-gray-500 mt-8">
            No items found for the selected filter.
          </p>
        )}
      </div>
    </section>
  );
}

