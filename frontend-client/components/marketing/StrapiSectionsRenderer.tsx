/**
 * Strapi Sections Renderer
 * Renders Dynamic Zone sections from Strapi CMS
 * Maps __component to React components
 */

import { StrapiSection } from '@/lib/cms';
import { HeaderNavBlock } from './blocks/HeaderNavBlock';
import { HeroBlock } from './blocks/HeroBlock';
import { FooterSimpleBlock } from './blocks/FooterSimpleBlock';
import { PartnersStripBlock } from './blocks/PartnersStripBlock';
import { FaqAccordionBlock } from './blocks/FaqAccordionBlock';
import { AmbassadorSectionBlock } from './blocks/AmbassadorSectionBlock';
import { FeatureSplitBlock } from './blocks/FeatureSplitBlock';
import { CardsRowsBlock } from './blocks/CardsRowsBlock';
import { FeaturesGridBlock } from './blocks/FeaturesGridBlock';
import { SecuritySpotlightBlock } from './blocks/SecuritySpotlightBlock';

/**
 * Normalize Strapi component UID
 * Handles both formats: "marketing.marketing-xxx" and "marketing.xxx"
 * Also handles "blocks.blocks-xxx" to "blocks.xxx"
 * Converts "marketing.marketing-xxx" to "marketing.xxx" for backward compatibility
 */
function normalizeComponentUid(uid: string): string {
  if (uid.startsWith('marketing.marketing-')) {
    return `marketing.${uid.replace('marketing.marketing-', '')}`;
  }
  if (uid.startsWith('blocks.blocks-')) {
    return `blocks.${uid.replace('blocks.blocks-', '')}`;
  }
  // Handle blocks.blocks-ambassador-section -> blocks.ambassador-section
  if (uid === 'blocks.blocks-ambassador-section') {
    return 'blocks.ambassador-section';
  }
  return uid;
}

/**
 * Render a single section
 */
function renderSection(section: StrapiSection, index: number) {
  const rawComponentType = section.__component;
  const componentType = normalizeComponentUid(rawComponentType);

  // DEV ONLY: Debug logging
  if (process.env.NODE_ENV === 'development') {
    console.log('[StrapiSectionsRenderer] Rendering section', {
      index,
      rawComponentType,
      normalizedComponentType: componentType,
      hasLogoText: !!section.logo_text,
      linksCount: section.links?.length || 0,
      links: section.links, // Afficher les liens complets pour debug
      sectionKeys: Object.keys(section), // Afficher toutes les clés disponibles
    });
  }

  // Render header-nav - handle multiple component UID variants
  if (componentType === 'marketing.header-nav' || 
      componentType === 'marketing.marketing-header-nav' ||
      componentType === 'blocks.header-nav') {
    if (process.env.NODE_ENV === 'development') {
      console.log('[StrapiSectionsRenderer] Header Nav section data', {
        componentType,
        logo_text: section.logo_text,
        hasLogo: !!section.logo,
        logo: section.logo,
        logoStructure: section.logo ? {
          hasData: !!section.logo.data,
          hasAttributes: !!section.logo.data?.attributes,
          url: section.logo.data?.attributes?.url,
        } : null,
        linksCount: section.links?.length || 0,
        links: section.links,
        linksStructure: section.links?.map((link: any, idx: number) => ({
          index: idx,
          hasLabel: !!link.label,
          hasHref: !!link.href,
          label: link.label,
          href: link.href,
          is_external: link.is_external,
        })),
        sectionKeys: Object.keys(section),
      });
    }
    
    return (
      <HeaderNavBlock
        key={index}
        logo_text={section.logo_text}
        logo={section.logo}
        links={section.links || []}
        primary_cta={section.primary_cta}
        cta_label={section.cta_label}
        cta_href={section.cta_href}
        sticky={section.sticky !== undefined ? section.sticky : true}
        theme={section.theme || 'light'}
      />
    );
  }

  // Render hero
  if (componentType === 'marketing.hero') {
    // Handle CTAs: can be single object (from component) or array (from repeatable component)
    const primaryCta = Array.isArray(section.primary_cta) 
      ? section.primary_cta[0] 
      : section.primary_cta;
    const secondaryCta = section.secondary_cta; // Already single object (repeatable: false)

    // DEV ONLY: Debug logging for hero
    if (process.env.NODE_ENV === 'development') {
      console.log('[StrapiSectionsRenderer] Hero section data', {
        title: section.title,
        subtitle: section.subtitle,
        description: section.description,
        hasBackgroundImage: !!(section.background_image || section.backgroundImage),
        backgroundImage: section.background_image,
        backgroundImageAlt: section.backgroundImage,
        primary_cta: section.primary_cta,
        primary_cta_type: Array.isArray(section.primary_cta) ? 'array' : typeof section.primary_cta,
        primaryCta: primaryCta,
        secondary_cta: section.secondary_cta,
        sectionKeys: Object.keys(section),
      });
    }

    return (
      <HeroBlock
        key={index}
        title={section.title || ''}
        subtitle={section.subtitle}
        description={section.description}
        eyebrow={section.eyebrow}
        background_image={section.background_image || section.backgroundImage}
        primary_cta={primaryCta}
        secondary_cta={secondaryCta}
        align={section.align || 'center'}
        theme={section.theme || 'dark'}
      />
    );
  }

  // Render cards-rows
  if (componentType === 'blocks.cards-rows') {
    // DEV ONLY: Debug logging for cards-rows
    if (process.env.NODE_ENV === 'development') {
      console.log('[StrapiSectionsRenderer] Cards rows section data', {
        title: section.title,
        subtitle: section.subtitle,
        rowsCount: section.rows?.length || 0,
        sectionKeys: Object.keys(section),
      });
    }

    return (
      <CardsRowsBlock
        key={index}
        title={section.title}
        subtitle={section.subtitle}
        rows={section.rows}
        anchor_id={section.anchor_id}
      />
    );
  }

  // Render feature-split
  if (componentType === 'blocks.feature-split') {
    // DEV ONLY: Debug logging for feature-split
    if (process.env.NODE_ENV === 'development') {
      console.log('[StrapiSectionsRenderer] Feature split section data', {
        eyebrow: section.eyebrow,
        eyebrow_variant: section.eyebrow_variant,
        title: section.title,
        hasDescription: !!section.description,
        hasMedia: !!section.media,
        layout: section.layout,
        hasCta: !!section.cta,
        sectionKeys: Object.keys(section),
      });
    }

    return (
      <FeatureSplitBlock
        key={index}
        eyebrow={section.eyebrow}
        eyebrow_variant={section.eyebrow_variant}
        title={section.title}
        description={section.description}
        media={section.media}
        layout={section.layout}
        cta={section.cta}
        anchor_id={section.anchor_id}
      />
    );
  }

  // Render ambassador-section
  if (componentType === 'blocks.ambassador-section') {
    // DEV ONLY: Debug logging for ambassador-section
    if (process.env.NODE_ENV === 'development') {
      console.log('[StrapiSectionsRenderer] Ambassador section data', {
        title: section.title,
        subtitle: section.subtitle,
        card_title: section.card_title,
        hasCardText: !!section.card_text,
        hasCta: !!section.cta,
        hasBackgroundImage: !!(section.background_image),
        overlay_opacity: section.overlay_opacity,
        card_height: section.card_height,
        content_max_width: section.content_max_width,
        align: section.align,
        sectionKeys: Object.keys(section),
      });
    }

    return (
      <AmbassadorSectionBlock
        key={index}
        title={section.title}
        subtitle={section.subtitle}
        card_title={section.card_title}
        card_text={section.card_text}
        cta={section.cta}
        background_image={section.background_image}
        overlay_opacity={section.overlay_opacity}
        card_height={section.card_height}
        content_max_width={section.content_max_width}
        align={section.align}
        anchor_id={section.anchor_id}
      />
    );
  }

  // Render faq-accordion
  if (componentType === 'blocks.faq-accordion') {
    // DEV ONLY: Debug logging for faq-accordion
    if (process.env.NODE_ENV === 'development') {
      console.log('[StrapiSectionsRenderer] FAQ accordion section data', {
        title: section.title,
        itemsCount: section.items?.length || 0,
        items: section.items?.map((item: any) => ({
          question: item.question,
          hasAnswer: !!item.answer,
          is_open_by_default: item.is_open_by_default,
        })),
        sectionKeys: Object.keys(section),
      });
    }

    return (
      <FaqAccordionBlock
        key={index}
        eyebrow={section.eyebrow}
        title={section.title}
        items={section.items || []}
      />
    );
  }

  // Render partners-strip
  if (componentType === 'blocks.partners-strip') {
    // DEV ONLY: Debug logging for partners-strip
    if (process.env.NODE_ENV === 'development') {
      console.log('[StrapiSectionsRenderer] Partners strip section data', {
        title: section.title,
        subtitle: section.subtitle,
        logosCount: section.logos?.length || 0,
        layout: section.layout,
        theme: section.theme,
        sectionKeys: Object.keys(section),
      });
    }

    return (
      <PartnersStripBlock
        key={index}
        title={section.title}
        subtitle={section.subtitle}
        partner_kind={section.partner_kind || 'all'}
        layout={section.layout || 'grid'}
        theme={section.theme || 'light'}
        show_names={section.show_names || false}
        grayscale={section.grayscale !== undefined ? section.grayscale : true}
        logos={section.logos || []}
      />
    );
  }

  // Render features-grid
  if (componentType === 'blocks.features-grid') {
    if (process.env.NODE_ENV === 'development') {
      console.log('[StrapiSectionsRenderer] Features Grid section data', {
        title: section.title,
        subtitle: section.subtitle,
        hasCta: !!section.cta,
        rowsCount: section.rows?.length || 0,
        sectionKeys: Object.keys(section),
      });
    }

    return (
      <FeaturesGridBlock
        key={index}
        title={section.title || ''}
        subtitle={section.subtitle}
        cta={section.cta}
        rows={section.rows || []}
        anchor_id={section.anchor_id}
      />
    );
  }

  // Render security-spotlight
  if (componentType === 'blocks.security-spotlight') {
    if (process.env.NODE_ENV === 'development') {
      console.log('[StrapiSectionsRenderer] Security Spotlight section data', {
        title: section.title,
        subtitle: section.subtitle,
        hasDescription: !!section.description,
        hasCta: !!section.cta,
        layout: section.layout,
        max_width: section.max_width,
        cardsCount: section.cards?.length || 0,
        emphasis_index: section.emphasis_index,
        sectionKeys: Object.keys(section),
      });
    }

    return (
      <SecuritySpotlightBlock
        key={index}
        title={section.title || ''}
        subtitle={section.subtitle}
        description={section.description}
        cta={section.cta}
        layout={section.layout || 'center-emphasis'} // Legacy support
        max_width={section.max_width || 'default'}
        cards={section.cards || []}
        responsive_mode={section.responsive_mode || 'carousel'}
        desktop_layout={section.desktop_layout || 'three-center-emphasis'}
        show_dots={section.show_dots !== undefined ? section.show_dots : true}
        infinite={section.infinite !== undefined ? section.infinite : true}
        start_position={section.start_position || 'center'}
        overlay_mode={section.overlay_mode || 'auto'}
        overlay_style={section.overlay_style || 'dark-gradient'}
        content_mode={section.content_mode || 'overlay'}
        panel_layout={section.panel_layout || 'content-left'}
        panel_align={section.panel_align || 'center'}
        panel_width={section.panel_width || 'md'}
        sidepanel_use_slide_content={section.sidepanel_use_slide_content !== undefined ? section.sidepanel_use_slide_content : true}
        sidepanel_fallback={section.sidepanel_fallback}
        sidepanel_cta={section.sidepanel_cta}
        sidepanel_show_dots={section.sidepanel_show_dots !== undefined ? section.sidepanel_show_dots : true}
        disable_overlay_in_sidepanel={section.disable_overlay_in_sidepanel !== undefined ? section.disable_overlay_in_sidepanel : true}
        image_fit={section.image_fit || 'contain'}
        emphasis_index={section.emphasis_index !== undefined ? section.emphasis_index : 1}
        anchor_id={section.anchor_id}
      />
    );
  }

  // Render footer-simple
  if (componentType === 'marketing.footer-simple') {
    // Handle copyright: can be 'copyright' or 'copyrightText' field
    const copyrightText = section.copyrightText || section.copyright;
    
    // Handle links: extract label, href, and is_external from link components
    const links = (section.links || []).map((link: any) => {
      // Handle both direct object and nested structure from Strapi
      const label = typeof link === 'object' && link !== null 
        ? (link.label || (link as any).label)
        : null;
      const href = typeof link === 'object' && link !== null
        ? (link.href || (link as any).href)
        : null;
      const isExternal = typeof link === 'object' && link !== null
        ? (link.is_external !== undefined ? link.is_external : (link as any).is_external)
        : false;
      
      if (!label || !href) {
        if (process.env.NODE_ENV === 'development') {
          console.warn('[StrapiSectionsRenderer] Invalid footer link format', link);
        }
        return null;
      }
      
      return { label, href, is_external: isExternal };
    }).filter(Boolean); // Remove null entries

    // DEV ONLY: Debug logging for footer
    if (process.env.NODE_ENV === 'development') {
      console.log('[StrapiSectionsRenderer] Footer section data', {
        copyrightText,
        linksCount: links.length,
        links,
        sectionKeys: Object.keys(section),
      });
    }

    return (
      <FooterSimpleBlock
        key={index}
        copyrightText={copyrightText}
        links={links}
      />
    );
  }

  // All other components return null (no error, no fallback)
  if (process.env.NODE_ENV === 'development') {
    console.log('[StrapiSectionsRenderer] Ignoring component', componentType);
  }
  return null;
}

export interface StrapiSectionsRendererProps {
  sections: StrapiSection[];
}

/**
 * Main renderer component
 */
export function StrapiSectionsRenderer({
  sections = [],
}: StrapiSectionsRendererProps) {
  if (!sections || sections.length === 0) {
    return null;
  }

  return (
    <>
      {sections.map((section, index) => renderSection(section, index))}
    </>
  );
}

