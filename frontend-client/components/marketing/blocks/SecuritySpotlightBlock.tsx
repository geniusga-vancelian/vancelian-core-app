/**
 * Security Spotlight Block - Swiper carousel (desktop + mobile)
 * Inspired by Revolut "Your money, protected" section
 */

'use client';

import { useState, useRef } from 'react';
import Link from 'next/link';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Pagination } from 'swiper/modules';
import type { Swiper as SwiperType } from 'swiper';
import 'swiper/css';
import 'swiper/css/pagination';
import { MarketingFeatureCard, MarketingFeatureCardProps } from '../atoms/MarketingFeatureCard';

export interface CtaLink {
  label: string;
  href: string;
  is_external?: boolean;
}

export interface SectionCopy {
  eyebrow?: string;
  title?: string;
  text?: string;
}

export interface SecuritySpotlightBlockProps {
  title: string;
  subtitle?: string;
  description?: string;
  cta?: CtaLink;
  layout?: 'center-emphasis' | 'three-equal';
  max_width?: 'narrow' | 'default' | 'wide';
  cards: MarketingFeatureCardProps[];
  responsive_mode?: 'carousel' | 'static';
  desktop_layout?: 'three-center-emphasis' | 'three-equal';
  show_dots?: boolean;
  infinite?: boolean;
  start_position?: 'left' | 'center';
  overlay_mode?: 'auto' | 'always' | 'never';
  overlay_style?: 'dark-gradient' | 'dark-solid' | 'none';
  content_mode?: 'overlay' | 'side-panel';
  panel_layout?: 'content-left' | 'content-right';
  panel_align?: 'top' | 'center';
  panel_width?: 'sm' | 'md' | 'lg';
  sidepanel_use_slide_content?: boolean;
  sidepanel_fallback?: SectionCopy;
  sidepanel_cta?: CtaLink;
  sidepanel_show_dots?: boolean;
  disable_overlay_in_sidepanel?: boolean;
  image_fit?: 'contain' | 'cover';
  emphasis_index?: number;
  anchor_id?: string;
}

// Helper to get max width classes
function getMaxWidthClass(maxWidth: string = 'default') {
  switch (maxWidth) {
    case 'narrow':
      return 'max-w-5xl';
    case 'wide':
      return 'max-w-7xl';
    case 'default':
    default:
      return 'max-w-6xl';
  }
}

export function SecuritySpotlightBlock({
  title,
  subtitle,
  description,
  cta,
  layout = 'center-emphasis', // Legacy support
  max_width = 'default',
  cards = [],
  responsive_mode = 'carousel',
  desktop_layout = 'three-center-emphasis',
  show_dots = true,
  infinite = true,
  start_position = 'center',
  overlay_mode = 'auto',
  overlay_style = 'dark-gradient',
  content_mode = 'overlay',
  panel_layout = 'content-left',
  panel_align = 'center',
  panel_width = 'md',
  sidepanel_use_slide_content = true,
  sidepanel_fallback,
  sidepanel_cta,
  sidepanel_show_dots = true,
  disable_overlay_in_sidepanel = true,
  image_fit = 'contain',
  emphasis_index = 1,
  anchor_id,
}: SecuritySpotlightBlockProps) {
  const swiperRef = useRef<SwiperType | null>(null);

  if (!cards || cards.length < 3) {
    return null;
  }

  // Use desktop_layout if provided, otherwise fallback to layout for backward compatibility
  const effectiveDesktopLayout = desktop_layout || (layout === 'center-emphasis' ? 'three-center-emphasis' : 'three-equal');

  // Compute initial slide index based on start_position
  const total = cards.length;
  const initialSlide = start_position === 'left'
    ? 0
    : Math.max(0, Math.floor((total - 1) / 2));
  
  // Initialize selectedIndex (used for side-panel sync) and activeIndex with initialSlide
  const [selectedIndex, setSelectedIndex] = useState(initialSlide);
  const [activeIndex, setActiveIndex] = useState(initialSlide);
  
  // Determine if we're in side-panel mode
  const isSidePanel = content_mode === 'side-panel';
  
  // Determine overlay mode: in side-panel mode, disable overlay if disable_overlay_in_sidepanel is true
  const effectiveOverlayMode = isSidePanel && disable_overlay_in_sidepanel 
    ? 'never' 
    : overlay_mode;

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

  // Determine panel content based on selected slide
  const selectedSlide = cards[selectedIndex] ?? cards[0];
  const panelFromSlide = sidepanel_use_slide_content !== false;
  
  const panelEyebrow = panelFromSlide ? selectedSlide?.eyebrow : (sidepanel_fallback?.eyebrow || undefined);
  const panelTitle = panelFromSlide ? selectedSlide?.title : (sidepanel_fallback?.title || undefined);
  const panelText = panelFromSlide ? selectedSlide?.text : (sidepanel_fallback?.text || undefined);
  
  // Use slide CTA if available, otherwise use section CTA
  const slideCtaOk = !!selectedSlide?.cta?.label && !!selectedSlide?.cta?.href;
  const sectionCtaOk = !!sidepanel_cta?.label && !!sidepanel_cta?.href;
  const panelCta = slideCtaOk ? selectedSlide.cta : (sectionCtaOk ? sidepanel_cta : undefined);
  
  // If panel content is empty and we have fallback, use it
  const finalPanelTitle = panelTitle || sidepanel_fallback?.title || undefined;
  const finalPanelText = panelText || sidepanel_fallback?.text || undefined;
  const finalPanelEyebrow = panelEyebrow || sidepanel_fallback?.eyebrow || undefined;

  const sectionProps: { id?: string; className: string } = {
    className: 'py-16 md:py-24 bg-[#272727]',
  };

  if (anchor_id) {
    sectionProps.id = anchor_id;
  }

  const maxWidthClass = getMaxWidthClass(max_width);
  
  // Panel width classes
  const panelWidthClass = panel_width === 'sm' ? 'max-w-md' : panel_width === 'lg' ? 'max-w-2xl' : 'max-w-xl';
  
  // Side Panel Component - Revolut-style design
  const SidePanel = ({ eyebrow, title, text, cta: panelCtaProp }: { eyebrow?: string; title?: string; text?: string; cta?: CtaLink }) => {
    if (!eyebrow && !title && !text && !panelCtaProp) {
      return null;
    }
    
    return (
      <div className={`flex flex-col justify-center ${panelWidthClass}`}>
        {eyebrow && (
          <div className="text-sm md:text-base text-neutral-400 uppercase tracking-wide mb-2">
            {eyebrow}
          </div>
        )}
        {title && (
          <h2 className="text-[36px] font-avenir font-light uppercase text-neutral-900 mb-4 md:mb-6">
            {title}
          </h2>
        )}
        {text && (
          <p className="text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 max-w-[42ch] text-neutral-600">
            {text}
          </p>
        )}
        {panelCtaProp?.label && panelCtaProp?.href && (
          <div>
            {panelCtaProp.is_external ? (
              <a
                href={panelCtaProp.href}
                className="inline-flex items-center justify-center rounded-lg bg-neutral-900 px-6 py-3 text-sm font-medium text-white hover:bg-neutral-800 transition-colors"
                target="_blank"
                rel="noreferrer"
              >
                {panelCtaProp.label}
              </a>
            ) : (
              <Link
                href={panelCtaProp.href}
                className="inline-flex items-center justify-center rounded-lg bg-neutral-900 px-6 py-3 text-sm font-medium text-white hover:bg-neutral-800 transition-colors"
              >
                {panelCtaProp.label}
              </Link>
            )}
          </div>
        )}
      </div>
    );
  };

  // Render carousel component (shared logic)
  const renderCarousel = () => {
    const effectiveShowDots = isSidePanel ? (sidepanel_show_dots !== false) : show_dots;
    
    // In side-panel mode: slides align to left, active slide is always first (leftmost)
    // The carousel should extend to the right edge of the screen (no container padding on right)
    const shouldCenterSlides = !isSidePanel;
    
    return (
      <div className={`${isSidePanel ? 'w-full -mr-4 md:-mr-6 lg:-mr-8 overflow-visible' : 'mx-auto max-w-5xl overflow-visible'}`}>
        <Swiper
          modules={effectiveShowDots ? [Pagination] : []}
          spaceBetween={isSidePanel ? 16 : 8}
          slidesPerView={isSidePanel ? 'auto' : "auto"}
          centeredSlides={false} // Never center in side-panel mode - active slide is always left
          initialSlide={isSidePanel ? 0 : initialSlide}
          loop={infinite && cards.length >= 3} // Enable loop for side-panel with enough cards
          loopedSlides={isSidePanel ? Math.min(cards.length, 5) : undefined} // Help with loop calculations
          grabCursor={true}
          watchSlidesProgress={true}
          slideToClickedSlide={false} // We handle clicks manually to ensure left positioning
          breakpoints={isSidePanel ? {
            0: {
              slidesPerView: 'auto',
              spaceBetween: 16,
            },
            640: {
              slidesPerView: 'auto',
              spaceBetween: 20,
            },
            768: {
              slidesPerView: 'auto',
              spaceBetween: 24,
            },
            1024: {
              slidesPerView: 'auto',
              spaceBetween: 28,
            },
          } : {
            0: {
              slidesPerView: 'auto',
              spaceBetween: 8,
            },
            640: {
              slidesPerView: 'auto',
              spaceBetween: 12,
            },
            768: {
              slidesPerView: 'auto',
              spaceBetween: 16,
            },
            1024: {
              slidesPerView: 'auto',
              spaceBetween: 20,
            },
          }}
          pagination={effectiveShowDots ? {
            clickable: true,
            dynamicBullets: false,
          } : false}
          onSwiper={(swiper) => {
            swiperRef.current = swiper;
            // In side-panel mode with loop, ensure we start at the correct slide
            if (isSidePanel && swiper) {
              // Set initial position to show selectedIndex as first slide
              if (swiper.slides && swiper.slides.length > 0) {
                swiper.slideToLoop(selectedIndex, 0);
              }
            }
          }}
          onSlideChange={(swiper) => {
            // Use realIndex for loop mode to get the actual slide index
            const newIndex = infinite && cards.length >= 3 ? swiper.realIndex : swiper.activeIndex;
            setActiveIndex(newIndex);
            setSelectedIndex(newIndex); // Sync selectedIndex for side-panel
          }}
          className={effectiveShowDots ? `pb-12 !overflow-visible` : `!overflow-visible`}
        >
          {cards.map((card, index) => {
            const isActive = activeIndex === index;
            
            // In side-panel mode: first slide (active) is larger, others are standard size
            // In overlay mode: keep existing centered behavior with scaling
            const slideWidthClass = isSidePanel
              ? isActive
                ? '!w-[320px] sm:!w-[380px] md:!w-[420px] lg:!w-[460px]' // Active slide (left) is larger
                : '!w-[280px] sm:!w-[320px] md:!w-[360px] lg:!w-[400px]' // Other slides are smaller
              : effectiveDesktopLayout === 'three-center-emphasis'
                ? '!w-[260px] sm:!w-[300px] md:!w-[320px] lg:!w-[280px] xl:!w-[300px]'
                : '!w-[260px] sm:!w-[300px] md:!w-[320px] lg:!w-[320px] xl:!w-[340px]';
            
            return (
              <SwiperSlide key={index} className={`!h-auto ${slideWidthClass} !overflow-visible`}>
                <div className={`h-full flex items-center ${isSidePanel ? 'justify-start' : 'justify-center'} ${isSidePanel ? 'py-4 md:py-6' : 'py-10 md:py-12'}`}>
                  {/* Scale wrapper - active slide in side-panel mode is larger via width, not scale transform */}
                  <div
                    className={`transition-all duration-300 ease-out will-change-transform transform-gpu [backface-visibility:hidden] ${isSidePanel ? 'origin-left' : 'origin-center'} ${
                      isSidePanel
                        ? 'scale-100 opacity-100' // No transform scaling, size controlled by width
                        : isActive
                          ? 'scale-[1.12] translate-y-0 opacity-100 z-20'
                          : 'scale-[0.94] translate-y-2 md:translate-y-3 opacity-70 z-10'
                    }`}
                  >
                    {/* Card component */}
                    <div
                      onClick={() => {
                        if (swiperRef.current) {
                          // In side-panel mode with loop: use slideToLoop to move clicked slide to position 0 (left)
                          if (isSidePanel && infinite && cards.length >= 3) {
                            swiperRef.current.slideToLoop(index, 300);
                          } else if (isSidePanel) {
                            swiperRef.current.slideTo(index, 300);
                          } else {
                            swiperRef.current.slideTo(index);
                          }
                          setSelectedIndex(index);
                        }
                      }}
                      className="cursor-pointer"
                    >
                      <MarketingFeatureCard
                        {...card}
                        image_fit={card.image_fit || image_fit}
                        isEmphasized={isActive} // Active slide is always emphasized (larger)
                        overlay_mode={effectiveOverlayMode}
                        overlay_style={overlay_style}
                      />
                    </div>
                  </div>
                </div>
              </SwiperSlide>
            );
          })}
        </Swiper>
      </div>
    );
  };

  // If side-panel mode, render different layout
  if (isSidePanel) {
    const alignClass = panel_align === 'top' ? 'items-start' : 'items-center';
    const isContentLeft = panel_layout === 'content-left';
    
    return (
      <section {...sectionProps}>
        <div className={`mx-auto ${maxWidthClass} ${isContentLeft ? 'pl-4 md:pl-6 lg:pl-8 pr-0' : 'pr-4 md:pr-6 lg:pr-8 pl-0'}`}>
          <div className={`grid ${alignClass} gap-8 md:gap-12 lg:gap-16 md:grid-cols-2`}>
            {isContentLeft ? (
              <>
                <SidePanel eyebrow={finalPanelEyebrow} title={finalPanelTitle} text={finalPanelText} cta={panelCta} />
                <div className="flex items-center justify-start overflow-visible w-full">
                  {renderCarousel()}
                </div>
              </>
            ) : (
              <>
                <div className="flex items-center justify-start overflow-visible w-full">
                  {renderCarousel()}
                </div>
                <SidePanel eyebrow={finalPanelEyebrow} title={finalPanelTitle} text={finalPanelText} cta={panelCta} />
              </>
            )}
          </div>
        </div>
      </section>
    );
  }

  // Original overlay mode layout
  return (
    <section {...sectionProps}>
      <div className={`mx-auto ${maxWidthClass} px-4 md:px-6`}>
        {/* Section Header */}
        <div className="text-center mb-12">
          <h2 className="text-[36px] font-avenir font-light uppercase text-gray-900 mb-4">
            {title}
          </h2>
          {subtitle && (
            <p className="text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 text-neutral-600">
              {subtitle}
            </p>
          )}
          {description && (
            <p className="text-[14px] font-avenir font-[350] leading-[160%] tracking-[0] mb-4 text-neutral-500 max-w-3xl mx-auto">
              {description}
            </p>
          )}
          {sectionCtaLink && (
            <div className="flex justify-center mt-6">
              {sectionCtaLink}
            </div>
          )}
        </div>

        {/* Cards Container - Swiper everywhere (desktop + mobile) */}
        {responsive_mode === 'carousel' ? (
          renderCarousel()
        ) : (
          // Static grid fallback (if responsive_mode=static)
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:hidden">
            {cards.map((card, index) => (
              <MarketingFeatureCard
                key={index}
                {...card}
                image_fit={card.image_fit || image_fit}
                isEmphasized={false}
                overlay_mode={effectiveOverlayMode}
                overlay_style={overlay_style}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
