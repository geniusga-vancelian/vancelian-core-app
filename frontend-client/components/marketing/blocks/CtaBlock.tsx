/**
 * CTA Block - Renders a call-to-action section from Strapi CMS
 * Used in Dynamic Zone sections
 */

export interface CtaBlockProps {
  title: string;
  subtitle?: string;
  ctaLabel?: string;
  ctaHref?: string;
}

export function CtaBlock({
  title,
  subtitle,
  ctaLabel,
  ctaHref,
}: CtaBlockProps) {
  return (
    <section className="py-16 md:py-24 bg-[#fab758] text-gray-900">
      <div className="container mx-auto px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            {title}
          </h2>
          
          {subtitle && (
            <p className="text-xl text-gray-800 mb-8">
              {subtitle}
            </p>
          )}
          
          {ctaLabel && ctaHref && (
            <a
              href={ctaHref}
              className="inline-block px-8 py-4 bg-gray-900 hover:bg-gray-800 text-white font-semibold rounded-lg transition-colors"
            >
              {ctaLabel}
            </a>
          )}
        </div>
      </div>
    </section>
  );
}


