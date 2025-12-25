/**
 * Marketing Feature Card - Reusable card component for feature/marketing blocks
 * Used by FeaturesGridBlock, SecuritySpotlightBlock, etc.
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
    console.warn('[MarketingFeatureCard] lucide-react not installed. Install it with: npm install lucide-react');
  }
}

export interface CtaLink {
  label: string;
  href: string;
  is_external?: boolean;
}

export interface MarketingFeatureCardProps {
  eyebrow?: string;
  title?: string;
  text?: string;
  bullet_type?: 'number' | 'icon';
  bullet_value?: string;
  // Backward compatibility (deprecated, use bullet_value instead)
  number?: number;
  icon?: string;
  card_theme?: 'light' | 'muted' | 'dark';
  accent?: 'none' | 'brand' | 'success' | 'warning' | 'info';
  image?: StrapiMedia;
  image_fit?: 'contain' | 'cover';
  cta?: CtaLink;
  className?: string;
  minHeight?: string;
  isEmphasized?: boolean;
  overlay_mode?: 'auto' | 'always' | 'never';
  overlay_style?: 'dark-gradient' | 'dark-solid' | 'none';
}

// Icon name mapping: enum value -> Lucide component name
const ICON_NAME_MAP: Record<string, string> = {
  'coins': 'Coins',
  'globe': 'Globe',
  'plus': 'Plus',
  'arrow-right': 'ArrowRight',
  'shield': 'Shield',
  'sparkles': 'Sparkles',
  'wallet': 'Wallet',
  'chart': 'BarChart3',
  'link': 'Link',
  'help-circle': 'HelpCircle',
  'bar-chart-3': 'BarChart3',
};

// Helper to get Lucide icon component by name with fallback
function getLucideIcon(iconName?: string) {
  if (!LucideIcons) {
    return null;
  }
  if (!iconName) {
    return LucideIcons.Sparkles || null;
  }
  
  // If iconName is an enum value (lowercase), map it to Lucide component name
  const lucideComponentName = ICON_NAME_MAP[iconName.toLowerCase()] || iconName;
  
  // Try to get the icon component
  const IconComponent = LucideIcons[lucideComponentName];
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
function getCardThemeClasses(theme: string = 'muted', isEmphasized: boolean = false) {
  const baseClasses = 'border';
  
  switch (theme) {
    case 'light':
      return `${baseClasses} bg-white border-gray-200 text-gray-900`;
    case 'dark':
      return `${baseClasses} bg-gray-900 text-white border-gray-800`;
    case 'muted':
    default:
      return `${baseClasses} bg-gray-50 text-gray-900 border-gray-100`;
  }
}

export function MarketingFeatureCard({
  eyebrow,
  title,
  text,
  bullet_type,
  bullet_value,
  number,
  icon,
  card_theme = 'muted',
  accent = 'brand',
  image,
  image_fit = 'contain',
  cta,
  className = '',
  minHeight,
  isEmphasized = false,
  overlay_mode = 'auto',
  overlay_style = 'dark-gradient',
}: MarketingFeatureCardProps) {
  // Backward compatibility: merge bullet_value with old number/icon fields
  // Priority: bullet_value > (icon enum mapped to Lucide name) > (number converted to string)
  let bulletValue = bullet_value;
  if (!bulletValue) {
    if (bullet_type === 'number') {
      bulletValue = number ? String(number) : '';
    } else if (bullet_type === 'icon') {
      // If icon is an enum value, map it to Lucide component name
      bulletValue = icon ? (ICON_NAME_MAP[icon.toLowerCase()] || icon) : '';
    }
  }

  // Determine if we should render a bullet
  const isNumberType = bullet_type === 'number';
  const isIconType = bullet_type === 'icon';
  
  // For number type: use bullet_value, or auto-generate from index if missing
  const numberValue = isNumberType && bulletValue ? bulletValue : null;
  
  // For icon type: use bullet_value to get icon component
  const IconComponent = isIconType && bulletValue ? getLucideIcon(bulletValue) : null;
  
  const themeClasses = getCardThemeClasses(card_theme, isEmphasized);
  const accentClasses = getAccentClasses(accent);
  const imageUrl = image ? getMediaUrl(image) : null;
  const isDark = card_theme === 'dark';

  // Get image dimensions from Strapi media data
  let imageWidth: number | null = null;
  let imageHeight: number | null = null;
  
  if (image && typeof image === 'object') {
    // Try to get dimensions from data.attributes
    if (image.data) {
      const imageData = Array.isArray(image.data) ? image.data[0] : image.data;
      if (imageData?.attributes) {
        imageWidth = imageData.attributes.width ?? null;
        imageHeight = imageData.attributes.height ?? null;
      }
      // Fallback: try direct width/height on data
      if (!imageWidth && 'width' in imageData) {
        imageWidth = (imageData as any).width ?? null;
      }
      if (!imageHeight && 'height' in imageData) {
        imageHeight = (imageData as any).height ?? null;
      }
    }
    // Fallback: try direct attributes on image
    if (!imageWidth && 'attributes' in image && image.attributes) {
      imageWidth = (image.attributes as any).width ?? null;
      imageHeight = (image.attributes as any).height ?? null;
    }
  }
  
  // Default aspect ratio if dimensions not available
  const aspectRatio = imageWidth && imageHeight ? `${imageWidth}/${imageHeight}` : null;

  // Determine if overlay should be shown
  const hasOverlayContent = () => {
    const hasEyebrow = !!eyebrow?.trim();
    const hasTitle = !!title?.trim();
    const hasText = !!text?.trim();
    const hasCta = !!cta?.label?.trim() && !!cta?.href?.trim();
    return hasEyebrow || hasTitle || hasText || hasCta;
  };

  const shouldShowOverlay = 
    overlay_mode === 'always'
      ? true
      : overlay_mode === 'never'
        ? false
        : hasOverlayContent(); // auto

  // Overlay style classes
  const overlayClass = shouldShowOverlay && overlay_style !== 'none'
    ? overlay_style === 'dark-solid'
      ? 'bg-black/45'
      : 'bg-gradient-to-t from-black/55 via-black/15 to-transparent'
    : '';

  // Render bullet if we have a number or icon
  const shouldRenderBullet = (isNumberType && numberValue) || (isIconType && IconComponent);

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

  // Determine if card has text content
  const hasTextContent = shouldShowOverlay || (!imageUrl);
  
  // Use aspectRatio STRICT if image dimensions available and no minHeight specified
  // But always apply a minimum height to prevent very small images
  // If no text content and only image, ensure minimum height
  const shouldUseAspectRatio = aspectRatio && !minHeight && imageUrl;
  let heightClass: string | undefined;
  
  if (minHeight) {
    heightClass = minHeight;
  } else if (shouldUseAspectRatio) {
    // If using aspectRatio, still apply min-height for image-only cards
    heightClass = hasTextContent 
      ? undefined // Let aspectRatio control if there's text content
      : (isEmphasized ? 'min-h-[400px]' : 'min-h-[350px]'); // Minimum height for image-only cards
  } else {
    heightClass = isEmphasized ? 'min-h-[520px]' : 'min-h-[420px]';
  }
  
  const paddingClass = isEmphasized ? 'p-8 md:p-10' : 'p-6 md:p-8';

  return (
    <div 
      className={`relative overflow-hidden rounded-[28px] ${themeClasses} ${paddingClass} flex flex-col ${heightClass || ''} ${className}`}
      {...(shouldUseAspectRatio ? { style: { aspectRatio } as React.CSSProperties } : {})}
    >
      {/* Background Image (if present) - object-contain by default, no forced height */}
      {imageUrl && (
        <div className="absolute inset-0 overflow-hidden z-0 bg-transparent">
          <Image
            src={imageUrl}
            alt={title || 'Card image'}
            fill
            className="object-contain object-center"
            sizes="(max-width: 768px) 100vw, 33vw"
            unoptimized={imageUrl.includes('localhost:1337')}
          />
          {/* Dark overlay for readability - conditional based on overlay_mode and overlay_style */}
          {shouldShowOverlay && overlayClass && (
            <div className={`absolute inset-0 ${overlayClass}`} />
          )}
        </div>
      )}

      {/* Content - only render if there's content to show */}
      {(shouldShowOverlay || !imageUrl) && (
        <div className={`relative ${imageUrl ? 'z-10' : ''} flex flex-col h-full`}>
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
        {eyebrow && (
          <div className="mb-2">
            <span className={`text-xs font-medium uppercase tracking-wide ${
              isDark ? 'text-white/70' : 'text-gray-500'
            }`}>
              {eyebrow}
            </span>
          </div>
        )}

        {/* Title (optional) */}
        {title && (
          <h3 className={`text-xl md:text-2xl font-bold mb-3 ${
            isDark ? 'text-white' : 'text-gray-900'
          } ${isEmphasized ? 'md:text-3xl' : ''}`}>
            {title}
          </h3>
        )}

        {/* Text (optional) */}
        {text && (
          <p className={`flex-1 text-base leading-relaxed ${
            isDark ? 'text-white/80' : 'text-gray-600'
          } ${isEmphasized ? 'md:text-lg' : ''}`}>
            {text}
          </p>
        )}

        {/* Card CTA (optional) */}
        {cta?.label && cta?.href && (
          <div className="mt-4">
            <CardCtaLink cardCta={cta} />
          </div>
        )}
        </div>
      )}
    </div>
  );
}
