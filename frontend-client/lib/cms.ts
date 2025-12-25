/**
 * CMS (Strapi) API client for frontend-client
 * All URLs use getStrapiApiUrl() or getStrapiBaseUrl() from config.ts (no hardcoding)
 */

import { getStrapiApiUrl, getStrapiBaseUrl } from './config';

/**
 * Build Strapi populate query string manually (without qs dependency)
 * Recursively builds nested populate queries for Strapi API
 */
function buildStrapiQuery(params: {
  filters?: Record<string, any>;
  locale?: string;
  populate?: Record<string, any>;
}): string {
  const parts: string[] = [];

  // Build filters
  if (params.filters) {
    Object.entries(params.filters).forEach(([key, value]) => {
      if (typeof value === 'object' && value !== null && '$eq' in value) {
        parts.push(`filters[${key}][$eq]=${encodeURIComponent(value.$eq)}`);
      } else if (typeof value === 'string' || typeof value === 'number') {
        parts.push(`filters[${key}]=${encodeURIComponent(value)}`);
      }
    });
  }

  // Build locale
  if (params.locale) {
    parts.push(`locale=${encodeURIComponent(params.locale)}`);
  }

  // Build populate (recursive)
  function buildPopulate(path: string, value: any): void {
    if (value === '*') {
      parts.push(`${path}=*`);
      return;
    }
    
    if (typeof value === 'object' && value !== null) {
      if ('populate' in value) {
        // Handle nested populate structure: { populate: { ... } }
        buildPopulate(`${path}[populate]`, value.populate);
      } else {
        // Handle object with keys: { key1: value1, key2: value2 }
        Object.entries(value).forEach(([key, val]) => {
          const newPath = `${path}[${key}]`;
          if (val === '*') {
            parts.push(`${newPath}=*`);
          } else if (typeof val === 'object' && val !== null) {
            buildPopulate(newPath, val);
          }
        });
      }
    }
  }

  if (params.populate) {
    Object.entries(params.populate).forEach(([key, value]) => {
      const path = `populate[${key}]`;
      if (value === '*') {
        parts.push(`${path}=*`);
      } else if (typeof value === 'object' && value !== null) {
        buildPopulate(path, value);
      }
    });
  }

  return parts.join('&');
}

export type Locale = 'fr' | 'en' | 'it';

export interface StrapiResponse<T> {
  data: T;
  meta?: {
    pagination?: {
      page: number;
      pageSize: number;
      pageCount: number;
      total: number;
    };
  };
}

export interface StrapiImage {
  id: number;
  attributes: {
    name: string;
    alternativeText?: string;
    caption?: string;
    width: number;
    height: number;
    formats?: {
      thumbnail?: { url: string };
      small?: { url: string };
      medium?: { url: string };
      large?: { url: string };
    };
    hash: string;
    ext: string;
    mime: string;
    size: number;
    url: string;
    previewUrl?: string;
    provider: string;
    createdAt: string;
    updatedAt: string;
  };
}

export interface StrapiMedia {
  data?: StrapiImage | StrapiImage[] | null;
  // Allow direct URL format (flattened)
  url?: string;
  // Allow flattened attributes
  attributes?: {
    url: string;
  };
  // Allow any other properties for flexibility
  [key: string]: any;
}

/**
 * Get public Strapi URL for images (always uses public URL, never internal Docker URL)
 * Images must be accessible from the browser, so we always use NEXT_PUBLIC_STRAPI_URL
 */
function getStrapiPublicBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_STRAPI_URL || process.env.STRAPI_URL;
  
  if (envUrl) {
    // Ensure it's an absolute URL
    if (!envUrl.startsWith('http://') && !envUrl.startsWith('https://')) {
      return `http://${envUrl}`;
    }
    return envUrl;
  }
  
  // Fallback to localhost for development
  return 'http://localhost:1337';
}

/**
 * Get media URL (handles both single and array, and various Strapi data formats)
 * Handles:
 * - Standard format: { data: { id, attributes: { url } } }
 * - Flat format: { data: { id, url, ... } } (attributes already flattened)
 * - Direct format: { url: '...' } (already flattened)
 * - Array format: { data: [{ ... }] }
 * - Direct string URL (for edge cases)
 * 
 * IMPORTANT: Always uses public URL (NEXT_PUBLIC_STRAPI_URL) so images are accessible from browser
 */
export function getMediaUrl(media: StrapiMedia | null | undefined | string): string | null {
  // Handle null/undefined
  if (!media) return null;
  
  // Handle direct string URL
  if (typeof media === 'string') {
    const baseUrl = getStrapiPublicBaseUrl();
    return media.startsWith('http') ? media : `${baseUrl}${media.startsWith('/') ? media : `/${media}`}`;
  }
  
  // Handle non-object types
  if (typeof media !== 'object') return null;
  
  try {
    const baseUrl = getStrapiPublicBaseUrl();
    
    // Handle direct URL format (already flattened, no data wrapper)
    if ('url' in media && typeof media.url === 'string' && media.url.length > 0) {
      const url = media.url;
      return url.startsWith('http') ? url : `${baseUrl}${url.startsWith('/') ? url : `/${url}`}`;
    }
    
    // Handle standard format with data wrapper
    if (media.data === null || media.data === undefined) return null;
    
    const image = Array.isArray(media.data) ? media.data[0] : media.data;
    if (!image || typeof image !== 'object') return null;
    
    // Try attributes.url (standard Strapi format)
    if (image.attributes && typeof image.attributes === 'object' && 'url' in image.attributes) {
      const url = image.attributes.url;
      if (typeof url === 'string' && url.length > 0) {
        return url.startsWith('http') ? url : `${baseUrl}${url.startsWith('/') ? url : `/${url}`}`;
      }
    }
    
    // Try direct url property (flattened format)
    if ('url' in image && typeof image.url === 'string' && image.url.length > 0) {
      const url = image.url;
      return url.startsWith('http') ? url : `${baseUrl}${url.startsWith('/') ? url : `/${url}`}`;
    }
    
    return null;
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[getMediaUrl] Error processing media:', error, media);
    }
    return null;
  }
}

/**
 * Global content (single type)
 */
export interface GlobalContent {
  site_name?: string;
  site_tagline?: string;
  default_seo_title?: string;
  default_seo_description?: string;
  default_seo_image?: StrapiMedia;
  social_links?: Array<{
    id: number;
    platform: string;
    url: string;
  }> | Record<string, string>;
  footer_legal?: string;
  support_email?: string;
}

/**
 * Get global content
 */
export async function getGlobal(locale: Locale = 'fr'): Promise<GlobalContent | null> {
  try {
    const url = getStrapiApiUrl(`global?locale=${locale}&populate=*`);
    const response = await fetch(url);
    if (!response.ok) {
      console.error(`[CMS] Failed to fetch global: ${response.status}`);
      return null;
    }
    const data: StrapiResponse<{ attributes: GlobalContent }> = await response.json();
    return data.data?.attributes || null;
  } catch (error) {
    console.error('[CMS] Error fetching global:', error);
    return null;
  }
}

/**
 * Page content
 */
export interface PageContent {
  slug: string;
  title: string;
  subtitle?: string;
  content?: string; // Rich text / markdown
  hero_image?: StrapiMedia;
  seo_title?: string;
  seo_description?: string;
  seo_image?: StrapiMedia;
  sections?: any[]; // Dynamic zone components (optional, for future)
}

/**
 * Get page by slug
 * @deprecated Use getPageBySlug instead (supports Dynamic Zone)
 */
export async function getPage(slug: string, locale: Locale = 'fr'): Promise<PageContent | null> {
  try {
    const url = getStrapiApiUrl(`pages?filters[slug][$eq]=${slug}&locale=${locale}&populate=*`);
    const response = await fetch(url);
    if (!response.ok) {
      console.error(`[CMS] Failed to fetch page ${slug}: ${response.status}`);
      return null;
    }
    const data: StrapiResponse<Array<{ attributes: PageContent }>> = await response.json();
    return data.data?.[0]?.attributes || null;
  } catch (error) {
    console.error(`[CMS] Error fetching page ${slug}:`, error);
    return null;
  }
}

/**
 * Dynamic Zone section component
 */
export interface StrapiSection {
  __component: string;
  [key: string]: any;
}

/**
 * Page with Dynamic Zone sections
 */
export interface PageWithSections {
  id: number;
  title: string;
  slug: string;
  seo_title?: string;
  seo_description?: string;
  seo_image?: StrapiMedia;
  sections?: StrapiSection[];
  publishedAt?: string;
  is_published?: boolean;
}

/**
 * Get page by slug with Dynamic Zone sections populated
 */
export async function getPageBySlug(slug: string, locale: Locale = 'fr'): Promise<PageWithSections | null> {
  try {
    const baseUrl = getStrapiBaseUrl();

    // Populate sections with all nested fields including media
    // For Dynamic Zones with nested components, Strapi v4 requires explicit populate for deeply nested fields
    // We build the query string manually to avoid qs dependency issues
    const query = buildStrapiQuery({
      filters: {
        slug: {
          $eq: slug,
        },
      },
      locale,
        populate: {
          sections: {
            populate: {
              logo: { populate: '*' }, // For header-nav logo
              links: { populate: '*' }, // For header-nav links (component marketing.link)
              logos: { populate: '*' }, // For partners-strip logos
              background_image: { populate: '*' }, // For hero/ambassador-section/cards-rows background image
              primary_cta: '*', // For hero primary CTA component
              secondary_cta: '*', // For hero secondary CTA component
              items: { populate: '*' }, // For FAQ accordion items
              cta: '*', // For ambassador-section and feature-split CTA component
              media: { populate: '*' }, // For feature-split media
            rows: {
              populate: {
                cards: {
                  populate: {
                    background_image: { populate: '*' }, // For cards-rows hero cards
                    cta: '*', // For cards-rows CTA component
                    image: { populate: '*' }, // For features-grid and security-spotlight card images
                  },
                },
              },
            },
            cards: { // For security-spotlight cards
              populate: {
                image: {
                  populate: '*', // Populate all image attributes including width/height
                },
                cta: '*', // Card CTA component
              },
            },
            sidepanel_fallback: '*', // Side panel fallback copy
            sidepanel_cta: '*', // Side panel CTA
          },
        },
        seo_image: '*',
      },
    });

    const url = `${baseUrl}/api/pages?${query}`;
    
    // Note: background_image populate should work for both hero and ambassador-section blocks

    if (process.env.NODE_ENV === 'development') {
      console.log('[CMS] Fetching page', { slug, locale, url, baseUrl, isServer: typeof window === 'undefined' });
    }

    const res = await fetch(url, { 
      cache: 'no-store',
      // Add headers for better compatibility
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!res.ok) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[CMS] Error fetching page', res.status, res.statusText, url);
      }
      return null;
    }

    const json = await res.json();

    const page = json?.data?.[0];

    if (!page) {
      if (process.env.NODE_ENV === 'development') {
        console.debug('[CMS] Page not found', { slug, locale });
      }
      return null;
    }

    // Return flattened object: { id, ...attributes }
    // Ensure sections is always an array (even if empty)
    const sections = page.attributes?.sections || [];
    
    // DEV ONLY: Debug logs
    if (process.env.NODE_ENV === 'development') {
      const componentTypes = sections.map((s: StrapiSection) => s.__component || 'unknown');
      
      // Debug hero section specifically to see if background_image is present
      const heroSection = sections.find((s: StrapiSection) => 
        s.__component === 'marketing.hero' || s.__component === 'marketing.marketing-hero'
      );
      
      console.debug('[CMS] Page fetched successfully', {
        slug,
        locale,
        sectionsCount: sections.length,
        componentTypes,
        pageId: page.id,
        hasSeoImage: !!page.attributes?.seo_image,
        heroSection: heroSection ? {
          __component: heroSection.__component,
          hasBackgroundImage: !!(heroSection.background_image || heroSection.backgroundImage),
          backgroundImageKeys: heroSection.background_image ? Object.keys(heroSection.background_image) : null,
          allKeys: Object.keys(heroSection),
        } : null,
      });
    }

    return {
      id: page.id,
      ...page.attributes,
      sections,
    };
  } catch (error) {
    // Handle fetch errors (network issues, DNS resolution, etc.)
    if (process.env.NODE_ENV === 'development') {
      console.error('[CMS] Fetch error for page', { slug, locale, error });
    }
    return null;
  }
}

/**
 * Offer Marketing content
 */
export interface OfferMarketing {
  offer_id: string; // UUID string from FastAPI
  title?: string;
  subtitle?: string;
  location?: string;
  highlights?: string[] | string; // Can be JSON string or array
  why_invest?: Array<{
    title: string;
    text: string;
    icon?: string;
  }>;
  metrics?: {
    target_yield?: number;
    investors_count?: number;
    days_left?: number;
  };
  breakdown?: {
    purchase_cost?: number;
    transaction_cost?: number;
    running_cost?: number;
    currency?: string;
  };
  cover_image?: StrapiMedia;
  gallery?: StrapiMedia;
  promo_video?: StrapiMedia;
  documents?: StrapiMedia;
}

/**
 * Get offer marketing content by offer_id
 */
export async function getOfferMarketing(offerId: string, locale: Locale = 'fr'): Promise<OfferMarketing | null> {
  try {
    const url = getStrapiApiUrl(`offer-marketings?filters[offer_id][$eq]=${offerId}&locale=${locale}&populate=*`);
    const response = await fetch(url);
    if (!response.ok) {
      if (response.status === 404) {
        // Content type may not exist yet - return null
        return null;
      }
      console.error(`[CMS] Failed to fetch offer marketing for ${offerId}: ${response.status}`);
      return null;
    }
    const data: StrapiResponse<Array<{ attributes: OfferMarketing }>> = await response.json();
    const marketing = data.data?.[0]?.attributes;
    
    // Parse highlights if it's a string (JSON)
    if (marketing?.highlights && typeof marketing.highlights === 'string') {
      try {
        marketing.highlights = JSON.parse(marketing.highlights);
      } catch {
        // If parsing fails, keep as string
      }
    }
    
    return marketing || null;
  } catch (error) {
    // Silently fail if Strapi is not available yet
    console.warn(`[CMS] Error fetching offer marketing for ${offerId}:`, error);
    return null;
  }
}

/**
 * Offer Update
 */
export interface OfferUpdate {
  offer_id: string;
  date: string;
  title: string;
  description?: string;
  status?: 'INFO' | 'MILESTONE' | 'SUCCESS' | 'WARNING';
  article_slug?: string; // Link to blog article (slug)
  media?: StrapiMedia;
}

/**
 * Get offer updates by offer_id
 */
export async function getOfferUpdates(offerId: string, locale: Locale = 'fr', limit: number = 10): Promise<OfferUpdate[]> {
  try {
    const url = getStrapiApiUrl(`offer-updates?filters[offer_id][$eq]=${offerId}&locale=${locale}&sort=date:desc&pagination[limit]=${limit}&populate=*`);
    const response = await fetch(url);
    if (!response.ok) {
      if (response.status === 404) {
        // Content type may not exist yet - return empty array
        return [];
      }
      console.error(`[CMS] Failed to fetch offer updates for ${offerId}: ${response.status}`);
      return [];
    }
    const data: StrapiResponse<Array<{ attributes: OfferUpdate }>> = await response.json();
    return data.data?.map(item => item.attributes) || [];
  } catch (error) {
    // Silently fail if Strapi is not available yet
    console.warn(`[CMS] Error fetching offer updates for ${offerId}:`, error);
    return [];
  }
}

/**
 * Article
 */
export interface Article {
  slug: string;
  title: string;
  excerpt?: string;
  content_markdown?: string;
  cover_image?: StrapiMedia;
  gallery?: StrapiMedia;
  promo_video?: StrapiMedia;
  published_at?: string;
  is_featured: boolean;
  offer_id?: string; // Optional UUID string
  seo?: {
    metaTitle?: string;
    metaDescription?: string;
    ogImage?: StrapiMedia;
  };
}

/**
 * Get articles
 */
export async function getArticles(options: {
  offerId?: string;
  locale?: Locale;
  limit?: number;
  status?: 'DRAFT' | 'PUBLISHED';
} = {}): Promise<Article[]> {
  try {
    const { offerId, locale = 'fr', limit = 25, status = 'PUBLISHED' } = options;
    let url = getStrapiApiUrl(`articles?filters[status][$eq]=${status}&locale=${locale}&sort=published_at:desc&pagination[limit]=${limit}&populate=*`);
    
    if (offerId) {
      // Filter by related_offer_ids containing the offerId
      url += `&filters[$or][0][related_offer_ids][$contains]=${offerId}`;
    }
    
    const response = await fetch(url);
    if (!response.ok) {
      if (response.status === 404) {
        return [];
      }
      console.error(`[CMS] Failed to fetch articles: ${response.status}`);
      return [];
    }
    const data: StrapiResponse<Array<{ attributes: Article }>> = await response.json();
    const articles = data.data?.map(item => {
      const attrs = item.attributes;
      // Parse related_offer_ids if it's a string (JSON)
      if (attrs.related_offer_ids && typeof attrs.related_offer_ids === 'string') {
        try {
          attrs.related_offer_ids = JSON.parse(attrs.related_offer_ids);
        } catch {
          // If parsing fails, keep as string
        }
      }
      return attrs;
    }) || [];
    
    // Additional client-side filtering by offerId if needed
    if (offerId && articles.length > 0) {
      return articles.filter(article => {
        if (!article.related_offer_ids) return false;
        const ids = Array.isArray(article.related_offer_ids) 
          ? article.related_offer_ids 
          : [article.related_offer_ids];
        return ids.includes(offerId);
      });
    }
    
    return articles;
  } catch (error) {
    console.warn('[CMS] Error fetching articles:', error);
    return [];
  }
}

/**
 * Get articles by offer ID (alias)
 */
export async function getArticlesByOfferId(offerId: string, locale: Locale = 'fr', limit: number = 10): Promise<Article[]> {
  return getArticles({ offerId, locale, limit, status: 'PUBLISHED' });
}

/**
 * Get article by slug
 */
export async function getArticle(slug: string, locale: Locale = 'fr'): Promise<Article | null> {
  try {
    const url = getStrapiApiUrl(`articles?filters[slug][$eq]=${slug}&locale=${locale}&populate=*`);
    const response = await fetch(url);
    if (!response.ok) {
      console.error(`[CMS] Failed to fetch article ${slug}: ${response.status}`);
      return null;
    }
    const data: StrapiResponse<Array<{ attributes: Article }>> = await response.json();
    return data.data?.[0]?.attributes || null;
  } catch (error) {
    console.error(`[CMS] Error fetching article ${slug}:`, error);
    return null;
  }
}

/**
 * Partner
 */
export interface Partner {
  slug: string;
  name: string;
  legal_name?: string;
  website?: string;
  country?: string;
  city?: string;
  description?: string; // Rich text / markdown
  logo?: StrapiMedia;
  cover_image?: StrapiMedia;
  ceo_name?: string;
  ceo_title?: string;
  ceo_photo?: StrapiMedia;
  ceo_message_quote?: string;
  ceo_bio_markdown?: string;
  videos?: StrapiMedia;
  documents?: StrapiMedia;
}

/**
 * Get partners
 */
export async function getPartners(locale: Locale = 'fr', limit: number = 50): Promise<Partner[]> {
  try {
    const url = getStrapiApiUrl(`partners?locale=${locale}&sort=name:asc&pagination[limit]=${limit}&populate=*`);
    const response = await fetch(url);
    if (!response.ok) {
      console.error(`[CMS] Failed to fetch partners: ${response.status}`);
      return [];
    }
    const data: StrapiResponse<Array<{ attributes: Partner }>> = await response.json();
    return data.data?.map(item => item.attributes) || [];
  } catch (error) {
    console.error('[CMS] Error fetching partners:', error);
    return [];
  }
}

/**
 * Get partner by slug
 */
export async function getPartner(slug: string, locale: Locale = 'fr'): Promise<Partner | null> {
  try {
    const url = getStrapiApiUrl(`partners?filters[slug][$eq]=${slug}&locale=${locale}&populate=*`);
    const response = await fetch(url);
    if (!response.ok) {
      console.error(`[CMS] Failed to fetch partner ${slug}: ${response.status}`);
      return null;
    }
    const data: StrapiResponse<Array<{ attributes: Partner }>> = await response.json();
    return data.data?.[0]?.attributes || null;
  } catch (error) {
    console.error(`[CMS] Error fetching partner ${slug}:`, error);
    return null;
  }
}

