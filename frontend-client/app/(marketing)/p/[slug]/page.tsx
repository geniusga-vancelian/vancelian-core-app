/**
 * Marketing Page - Clean URL route for Strapi pages
 * Route: /p/[slug]?locale=fr
 * Renders pages from Strapi CMS via Dynamic Zone
 */

import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getPageBySlug, getMediaUrl, Locale } from '@/lib/cms';
import { getStrapiBaseUrl } from '@/lib/config';
import { StrapiSectionsRenderer } from '@/components/marketing/StrapiSectionsRenderer';

interface MarketingPageProps {
  params: {
    slug: string;
  };
  searchParams: {
    locale?: string;
  };
}

/**
 * Generate metadata for SEO
 * Uses Strapi page data: seo_title, seo_description, seo_image
 */
export async function generateMetadata({
  params,
  searchParams,
}: MarketingPageProps): Promise<Metadata> {
  const locale = (searchParams.locale as Locale) || 'fr';
  const { slug } = params;

  try {
    const page = await getPageBySlug(slug, locale);

    if (!page) {
      return {
        title: 'Page not found',
      };
    }

    // SEO fields from Strapi (fallback to title if seo_title not set)
    const seoTitle = page.seo_title ?? page.title ?? 'Vancelian';
    const seoDescription = page.seo_description ?? '';
    const seoImage = getMediaUrl(page.seo_image);
    
    // Ensure absolute URL for OpenGraph image
    let absoluteImageUrl: string | undefined;
    if (seoImage) {
      absoluteImageUrl = seoImage.startsWith('http')
        ? seoImage
        : `${getStrapiBaseUrl().replace('/api', '')}${seoImage.startsWith('/') ? seoImage : `/${seoImage}`}`;
    }

    const baseUrl = typeof window !== 'undefined'
      ? window.location.origin
      : process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';
    
    const canonicalUrl = `${baseUrl}/p/${slug}${locale !== 'fr' ? `?locale=${locale}` : ''}`;

    return {
      title: seoTitle,
      description: seoDescription || undefined,
      alternates: {
        canonical: canonicalUrl,
      },
      openGraph: {
        title: seoTitle,
        description: seoDescription || undefined,
        images: absoluteImageUrl ? [absoluteImageUrl] : undefined,
        url: canonicalUrl,
      },
    };
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[Marketing Page] Error generating metadata:', error);
    }
    return {
      title: 'Vancelian',
    };
  }
}

/**
 * Marketing Page Component
 * Server Component - fetches data from Strapi and renders sections
 * NO mock data, NO hardcoded content - everything comes from Strapi
 */
export default async function MarketingPage({
  params,
  searchParams,
}: MarketingPageProps) {
  const locale = (searchParams.locale as Locale) || 'fr';
  const { slug } = params;

  // Fetch page from Strapi (source of truth)
  // Try current locale first, fallback to 'en' if page doesn't exist
  let page = await getPageBySlug(slug, locale);
  
  // Fallback to 'en' if page doesn't exist in requested locale
  if (!page && locale !== 'en') {
    page = await getPageBySlug(slug, 'en');
  }

  // If page still not found, return 404
  if (!page) {
    notFound();
  }

  // Render page with sections from Strapi Dynamic Zone
  // Order is EXACTLY as defined in Strapi
  const sections = page.sections || [];

  // DEV ONLY: Debug logging
  if (process.env.NODE_ENV === 'development') {
    console.log('[Marketing Page] Rendering page', {
      slug,
      locale,
      sectionsCount: sections.length,
      sections: sections.map((s: any) => ({
        __component: s.__component,
        logo_text: s.logo_text,
        linksCount: s.links?.length || 0,
      })),
    });
  }

  return (
    <main className="min-h-screen bg-white">
      {/* DEV ONLY: Message if page exists but has no sections */}
      {process.env.NODE_ENV === 'development' && sections.length === 0 && (
        <div className="py-8 px-4 bg-yellow-50 border border-yellow-200 rounded-lg m-4">
          <p className="text-yellow-800 text-sm font-semibold">
            No sections for this page
          </p>
          <p className="text-yellow-700 text-xs mt-1">
            Page: <code className="bg-yellow-100 px-2 py-1 rounded">{slug}</code> (locale: {locale})
          </p>
        </div>
      )}

      {/* Render all sections from Dynamic Zone */}
      <StrapiSectionsRenderer sections={sections} />
    </main>
  );
}

