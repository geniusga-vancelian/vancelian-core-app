/**
 * FAQ Accordion Block - Displays FAQ items in an accordion format
 * Tailwind CSS only, no external dependencies
 */

'use client';

import { useState, useEffect } from 'react';

export interface FaqItem {
  id?: number;
  question: string;
  answer?: string;
  is_open_by_default?: boolean;
}

export interface FaqAccordionBlockProps {
  eyebrow?: string;
  title?: string;
  items?: FaqItem[];
}

export function FaqAccordionBlock({
  eyebrow,
  title,
  items = [],
}: FaqAccordionBlockProps) {
  // Find initial open indexes: all items with is_open_by_default === true
  const getInitialOpenIndexes = (itemsList: FaqItem[]) => {
    const defaultOpenIndexes = new Set<number>();
    itemsList.forEach((item, index) => {
      if (item.is_open_by_default === true) {
        defaultOpenIndexes.add(index);
      }
    });
    return defaultOpenIndexes;
  };

  const [openIndexes, setOpenIndexes] = useState<Set<number>>(() => getInitialOpenIndexes(items));

  // Update openIndexes if items change
  useEffect(() => {
    setOpenIndexes(getInitialOpenIndexes(items));
  }, [items]);

  // Toggle accordion item (independent - multiple can be open at once)
  const toggleItem = (index: number) => {
    setOpenIndexes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  if (items.length === 0) {
    return null;
  }

  return (
    <section className="py-16 md:py-24 bg-[#272727]">
      <div className="max-w-4xl mx-auto px-4">
        {/* Eyebrow and Title */}
        {(eyebrow || title) && (
          <div className="text-center mb-12">
            {eyebrow && (
              <p className="text-xs font-medium tracking-[0.15em] uppercase text-gray-600 mb-3">
                {eyebrow}
              </p>
            )}
            {title && (
              <h2 className="text-[36px] font-avenir font-light uppercase text-gray-900">
                {title}
              </h2>
            )}
          </div>
        )}

        {/* Accordion Items */}
        <div className="space-y-3">
          {items.map((item, index) => {
            const isOpen = openIndexes.has(index);
            
            return (
              <div
                key={item.id || index}
                className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden transition-all duration-200"
              >
                {/* Question Header */}
                <button
                  type="button"
                  onClick={() => toggleItem(index)}
                  className="w-full flex items-center justify-between p-5 text-left hover:bg-gray-100/50 transition-colors"
                  aria-expanded={isOpen}
                  aria-controls={`faq-answer-${index}`}
                >
                  <span className="text-base font-semibold text-gray-900 pr-4">
                    {item.question}
                  </span>
                  
                  {/* Chevron Icon */}
                  <svg
                    className={`flex-shrink-0 w-5 h-5 text-gray-600 transition-transform duration-300 ${
                      isOpen ? 'transform rotate-180' : ''
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>

                {/* Answer Content */}
                <div
                  id={`faq-answer-${index}`}
                  className={`grid transition-all duration-300 ease-in-out ${
                    isOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
                  }`}
                >
                  <div className="overflow-hidden">
                    <div className="px-5 pb-5 pt-0">
                      <p className="text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 text-gray-600 whitespace-pre-line">
                        {item.answer || ''}
                      </p>
                    </div>
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

