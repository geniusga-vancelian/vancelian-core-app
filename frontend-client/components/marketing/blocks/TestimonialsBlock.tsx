/**
 * Testimonials Block - Renders testimonials from Strapi CMS
 * Used in Dynamic Zone sections
 */

'use client';

import { useState, useEffect } from 'react';
import { getMediaUrl, StrapiMedia } from '@/lib/cms';
import { getStrapiBaseUrl } from '@/lib/config';

export interface Testimonial {
  quote: string;
  author_name: string;
  author_title?: string;
  author_avatar?: StrapiMedia;
  company?: string;
  rating?: number;
}

export interface TestimonialsBlockProps {
  title?: string;
  subtitle?: string;
  items?: Testimonial[];
  variant?: 'grid' | 'slider';
  auto_advance?: boolean;
  interval_ms?: number;
}

function getAvatarUrl(media: StrapiMedia | undefined): string | null {
  if (!media) return null;
  const url = getMediaUrl(media);
  if (!url) return null;
  if (url.startsWith('http')) return url;
  const baseUrl = getStrapiBaseUrl().replace('/api', '');
  return `${baseUrl}${url.startsWith('/') ? url : `/${url}`}`;
}

function renderStars(rating?: number) {
  if (!rating || rating < 1 || rating > 5) return null;
  
  return (
    <div className="flex gap-1 mb-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <svg
          key={i}
          className={`w-5 h-5 ${
            i < rating ? 'text-[#fab758]' : 'text-gray-300'
          }`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </div>
  );
}

export function TestimonialsBlock({
  title,
  subtitle,
  items = [],
  variant = 'slider',
  auto_advance = false,
  interval_ms = 6000,
}: TestimonialsBlockProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (!auto_advance || variant !== 'slider' || items.length <= 1) {
      return;
    }

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % items.length);
    }, interval_ms);

    return () => clearInterval(interval);
  }, [auto_advance, variant, items.length, interval_ms]);

  if (items.length === 0) {
    return null;
  }

  const nextTestimonial = () => {
    setCurrentIndex((prev) => (prev + 1) % items.length);
  };

  const prevTestimonial = () => {
    setCurrentIndex((prev) => (prev - 1 + items.length) % items.length);
  };

  if (variant === 'grid') {
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {items.map((item, index) => {
              const avatarUrl = getAvatarUrl(item.author_avatar);
              
              return (
                <div
                  key={index}
                  className="bg-gray-50 rounded-lg p-6 border border-gray-200 hover:shadow-lg transition-shadow"
                >
                  {renderStars(item.rating)}
                  <p className="text-gray-700 mb-6 italic">
                    "{item.quote}"
                  </p>
                  <div className="flex items-center gap-4">
                    {avatarUrl && (
                      <img
                        src={avatarUrl}
                        alt={item.author_name}
                        className="w-12 h-12 rounded-full object-cover"
                      />
                    )}
                    <div>
                      <div className="font-semibold text-gray-900">
                        {item.author_name}
                      </div>
                      {(item.author_title || item.company) && (
                        <div className="text-sm text-gray-600">
                          {item.author_title}
                          {item.author_title && item.company && ', '}
                          {item.company}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>
    );
  }

  // Slider variant
  const currentItem = items[currentIndex];
  const avatarUrl = getAvatarUrl(currentItem.author_avatar);

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
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-lg p-8 md:p-12 shadow-lg border border-gray-200">
            {renderStars(currentItem.rating)}
            <blockquote className="text-xl md:text-2xl text-gray-700 mb-8 italic">
              "{currentItem.quote}"
            </blockquote>
            <div className="flex items-center gap-4">
              {avatarUrl && (
                <img
                  src={avatarUrl}
                  alt={currentItem.author_name}
                  className="w-16 h-16 rounded-full object-cover"
                />
              )}
              <div>
                <div className="text-lg font-semibold text-gray-900">
                  {currentItem.author_name}
                </div>
                {(currentItem.author_title || currentItem.company) && (
                  <div className="text-gray-600">
                    {currentItem.author_title}
                    {currentItem.author_title && currentItem.company && ', '}
                    {currentItem.company}
                  </div>
                )}
              </div>
            </div>
          </div>

          {items.length > 1 && (
            <div className="flex items-center justify-center gap-4 mt-8">
              <button
                onClick={prevTestimonial}
                className="p-2 rounded-full bg-white hover:bg-gray-100 border border-gray-200 transition-colors"
                aria-label="Previous testimonial"
              >
                <svg
                  className="w-6 h-6 text-gray-700"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              
              <div className="flex gap-2">
                {items.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentIndex(index)}
                    className={`w-2 h-2 rounded-full transition-colors ${
                      index === currentIndex
                        ? 'bg-[#fab758]'
                        : 'bg-gray-300'
                    }`}
                    aria-label={`Go to testimonial ${index + 1}`}
                  />
                ))}
              </div>

              <button
                onClick={nextTestimonial}
                className="p-2 rounded-full bg-white hover:bg-gray-100 border border-gray-200 transition-colors"
                aria-label="Next testimonial"
              >
                <svg
                  className="w-6 h-6 text-gray-700"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

