/**
 * Marketing Site Page - Renders Strapi CMS pages via Dynamic Zone
 * Route: /site?locale=fr (or / if home)
 */

import { Metadata } from 'next';
import { getPageBySlug, getMediaUrl, Locale } from '@/lib/cms';
import { StrapiSectionsRenderer } from '@/components/marketing/StrapiSectionsRenderer';

interface SitePageProps {
  searchParams: {
    locale?: string;
    slug?: string;
  };
}

/**
 * Generate metadata for SEO
 */
export async function generateMetadata({
  searchParams,
}: SitePageProps): Promise<Metadata> {
  const locale = (searchParams.locale as Locale) || 'fr';
  const slug = searchParams.slug || 'home';

  try {
    const page = await getPageBySlug(slug, locale);

    if (!page) {
      return {
        title: 'Page not found',
      };
    }

    const seoTitle = page.seo_title || page.title;
    const seoDescription = page.seo_description || undefined;
    const seoImage = getMediaUrl(page.seo_image);

    return {
      title: seoTitle,
      description: seoDescription,
      openGraph: {
        title: seoTitle,
        description: seoDescription,
        images: seoImage ? [seoImage] : undefined,
      },
    };
  } catch (error) {
    console.error('[Site Page] Error generating metadata:', error);
    return {
      title: 'Vancelian',
    };
  }
}

/**
 * Site Page Component
 */
export default async function SitePage({ searchParams }: SitePageProps) {
  const locale = (searchParams.locale as Locale) || 'fr';
  const slug = searchParams.slug || 'home';

  // Fetch page from Strapi
  let page;
  let error: string | null = null;

  try {
    page = await getPageBySlug(slug, locale);
    
    if (!page) {
      error = 'Page not found';
    }
  } catch (err) {
    console.error('[Site Page] Error fetching page:', err);
    error = 'CMS unavailable';
  }

  // Handle errors gracefully
  if (error || !page) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center px-4">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {error === 'Page not found' ? 'Page not found' : 'CMS unavailable'}
          </h1>
          <p className="text-gray-600 mb-4">
            {error === 'Page not found'
              ? `The page "${slug}" could not be found.`
              : 'The content management system is currently unavailable. Please try again later.'}
          </p>
          <a
            href="/"
            className="text-[#fab758] hover:underline"
          >
            Return to home
          </a>
        </div>
      </div>
    );
  }

  // Render page with sections
  return (
    <main className="min-h-screen">
      {/* Render all sections from Dynamic Zone */}
      <StrapiSectionsRenderer sections={page.sections || []} />
    </main>
  );
}


