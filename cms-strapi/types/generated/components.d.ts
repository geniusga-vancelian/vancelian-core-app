import type { Attribute, Schema } from '@strapi/strapi';

export interface AtomsCardsRow extends Schema.Component {
  collectionName: 'components_atoms_cards_rows';
  info: {
    description: 'A row containing 1 or 2 hero cards with a specific layout';
    displayName: 'cards-row';
  };
  attributes: {
    cards: Attribute.Component<'atoms.hero-card', true> &
      Attribute.Required &
      Attribute.SetMinMax<
        {
          max: 2;
          min: 1;
        },
        number
      >;
    gap: Attribute.Integer & Attribute.DefaultTo<24>;
    layout: Attribute.Enumeration<
      [
        'one-full',
        'two-50-50',
        'two-60-40',
        'two-40-60',
        'two-70-30',
        'two-30-70',
        'two-75-25',
        'two-25-75'
      ]
    > &
      Attribute.Required &
      Attribute.DefaultTo<'two-50-50'>;
  };
}

export interface AtomsCtaLink extends Schema.Component {
  collectionName: 'components_atoms_cta_links';
  info: {
    description: 'Call-to-action link with label, href, and external flag';
    displayName: 'cta-link';
  };
  attributes: {
    href: Attribute.String & Attribute.Required;
    is_external: Attribute.Boolean & Attribute.DefaultTo<false>;
    label: Attribute.String & Attribute.Required;
  };
}

export interface AtomsFaqItem extends Schema.Component {
  collectionName: 'components_atoms_faq_items';
  info: {
    description: 'Single FAQ question and answer item';
    displayName: 'faq-item';
  };
  attributes: {
    answer: Attribute.Text & Attribute.Required;
    is_open_by_default: Attribute.Boolean & Attribute.DefaultTo<false>;
    question: Attribute.String & Attribute.Required;
  };
}

export interface AtomsFeatureCard extends Schema.Component {
  collectionName: 'components_atoms_feature_cards';
  info: {
    description: 'Feature card with bullet (number or icon), title, text, optional image and CTA';
    displayName: 'feature-card';
  };
  attributes: {
    accent: Attribute.Enumeration<
      ['none', 'brand', 'success', 'warning', 'info']
    > &
      Attribute.DefaultTo<'brand'>;
    bullet_type: Attribute.Enumeration<['number', 'icon']> &
      Attribute.Required &
      Attribute.DefaultTo<'icon'>;
    bullet_value: Attribute.String;
    card_theme: Attribute.Enumeration<['light', 'muted', 'dark']> &
      Attribute.DefaultTo<'muted'>;
    cta: Attribute.Component<'atoms.cta-link'>;
    eyebrow: Attribute.String;
    icon: Attribute.Enumeration<
      [
        'coins',
        'globe',
        'plus',
        'arrow-right',
        'shield',
        'sparkles',
        'wallet',
        'chart',
        'link',
        'help-circle',
        'bar-chart-3'
      ]
    >;
    image: Attribute.Media<'images'>;
    number: Attribute.Integer &
      Attribute.SetMinMax<
        {
          min: 1;
        },
        number
      >;
    text: Attribute.Text;
    title: Attribute.String;
  };
}

export interface AtomsFeaturesRow extends Schema.Component {
  collectionName: 'components_atoms_features_rows';
  info: {
    description: 'A row of feature cards with column configuration';
    displayName: 'features-row';
  };
  attributes: {
    cards: Attribute.Component<'atoms.feature-card', true> &
      Attribute.Required &
      Attribute.SetMinMax<
        {
          max: 4;
          min: 2;
        },
        number
      >;
    columns: Attribute.Enumeration<['two', 'three', 'four']> &
      Attribute.Required &
      Attribute.DefaultTo<'three'>;
  };
}

export interface AtomsHeroCard extends Schema.Component {
  collectionName: 'components_atoms_hero_cards';
  info: {
    description: 'Hero card with background image, overlay, text, and optional CTA';
    displayName: 'hero-card';
  };
  attributes: {
    background_image: Attribute.Media<'images'> & Attribute.Required;
    cta: Attribute.Component<'atoms.cta-link'>;
    description: Attribute.Text & Attribute.Required;
    eyebrow: Attribute.String;
    text_position: Attribute.Enumeration<
      [
        'top-left',
        'center-left',
        'bottom-left',
        'top-center',
        'center-center',
        'bottom-center',
        'top-right',
        'center-right',
        'bottom-right'
      ]
    > &
      Attribute.Required &
      Attribute.DefaultTo<'center-left'>;
    title: Attribute.String & Attribute.Required;
  };
}

export interface AtomsPartnerLogo extends Schema.Component {
  collectionName: 'components_atoms_partner_logos';
  info: {
    description: 'Single partner logo with metadata';
    displayName: 'partner-logo';
  };
  attributes: {
    is_featured: Attribute.Boolean & Attribute.DefaultTo<false>;
    logo: Attribute.Media<'images'> & Attribute.Required;
    name: Attribute.String & Attribute.Required;
    order: Attribute.Integer;
    type: Attribute.Enumeration<['media', 'financial', 'technology']> &
      Attribute.Required &
      Attribute.DefaultTo<'technology'>;
    url: Attribute.String;
  };
}

export interface AtomsSectionCopy extends Schema.Component {
  collectionName: 'components_atoms_section_copies';
  info: {
    description: 'Section copy content with eyebrow, title, and text';
    displayName: 'section-copy';
  };
  attributes: {
    eyebrow: Attribute.String;
    text: Attribute.Text;
    title: Attribute.String;
  };
}

export interface BlocksAmbassadorSection extends Schema.Component {
  collectionName: 'components_blocks_ambassador_sections';
  info: {
    description: 'Ambassador/partnership section with card and CTA';
    displayName: 'ambassador-section';
  };
  attributes: {
    align: Attribute.Enumeration<['left', 'center']> &
      Attribute.DefaultTo<'left'>;
    anchor_id: Attribute.String;
    background_image: Attribute.Media<'images'>;
    card_height: Attribute.Enumeration<['md', 'lg', 'xl']> &
      Attribute.DefaultTo<'lg'>;
    card_text: Attribute.Text & Attribute.Required;
    card_title: Attribute.String & Attribute.Required;
    content_max_width: Attribute.Enumeration<['sm', 'md', 'lg']> &
      Attribute.DefaultTo<'md'>;
    cta: Attribute.Component<'atoms.cta-link'> & Attribute.Required;
    overlay_opacity: Attribute.Integer &
      Attribute.SetMinMax<
        {
          max: 85;
          min: 0;
        },
        number
      > &
      Attribute.DefaultTo<35>;
    subtitle: Attribute.String & Attribute.Required;
    title: Attribute.String & Attribute.Required;
  };
}

export interface BlocksCardsRows extends Schema.Component {
  collectionName: 'components_blocks_cards_rows';
  info: {
    description: 'Section with multiple rows of hero cards';
    displayName: 'cards-rows';
  };
  attributes: {
    anchor_id: Attribute.String;
    rows: Attribute.Component<'atoms.cards-row', true> &
      Attribute.Required &
      Attribute.SetMinMax<
        {
          min: 1;
        },
        number
      >;
    subtitle: Attribute.String;
    title: Attribute.String;
  };
}

export interface BlocksFaqAccordion extends Schema.Component {
  collectionName: 'components_blocks_faq_accordions';
  info: {
    description: 'FAQ section with accordion items';
    displayName: 'faq-accordion';
  };
  attributes: {
    eyebrow: Attribute.String;
    items: Attribute.Component<'atoms.faq-item', true> &
      Attribute.Required &
      Attribute.SetMinMax<
        {
          min: 1;
        },
        number
      >;
    title: Attribute.String & Attribute.Required;
  };
}

export interface BlocksFeatureSplit extends Schema.Component {
  collectionName: 'components_blocks_feature_splits';
  info: {
    description: 'Split section with text and image (image left or right)';
    displayName: 'feature-split';
  };
  attributes: {
    anchor_id: Attribute.String;
    cta: Attribute.Component<'atoms.cta-link'>;
    description: Attribute.Text & Attribute.Required;
    eyebrow: Attribute.String;
    eyebrow_variant: Attribute.Enumeration<['neutral', 'green', 'purple']> &
      Attribute.DefaultTo<'neutral'>;
    layout: Attribute.Enumeration<['image_right', 'image_left']> &
      Attribute.Required &
      Attribute.DefaultTo<'image_right'>;
    media: Attribute.Media<'images'> & Attribute.Required;
    title: Attribute.String & Attribute.Required;
  };
}

export interface BlocksFeaturesGrid extends Schema.Component {
  collectionName: 'components_blocks_features_grids';
  info: {
    description: 'Grid of feature cards organized in rows, similar to Revolut steps section';
    displayName: 'features-grid';
  };
  attributes: {
    anchor_id: Attribute.String;
    cta: Attribute.Component<'atoms.cta-link'>;
    rows: Attribute.Component<'atoms.features-row', true> &
      Attribute.Required &
      Attribute.SetMinMax<
        {
          min: 1;
        },
        number
      >;
    subtitle: Attribute.String;
    title: Attribute.String & Attribute.Required;
  };
}

export interface BlocksPartnersStrip extends Schema.Component {
  collectionName: 'components_blocks_partners_strips';
  info: {
    description: 'Partners / Logos strip block';
    displayName: 'partners-strip';
  };
  attributes: {
    grayscale: Attribute.Boolean & Attribute.DefaultTo<true>;
    layout: Attribute.Enumeration<['grid', 'carousel']> &
      Attribute.DefaultTo<'grid'>;
    logos: Attribute.Component<'atoms.partner-logo', true> & Attribute.Required;
    partner_kind: Attribute.Enumeration<
      ['all', 'media', 'financial', 'technology']
    > &
      Attribute.DefaultTo<'all'>;
    show_names: Attribute.Boolean & Attribute.DefaultTo<false>;
    subtitle: Attribute.String;
    theme: Attribute.Enumeration<['light', 'dark']> &
      Attribute.DefaultTo<'light'>;
    title: Attribute.String;
  };
}

export interface BlocksSecuritySpotlight extends Schema.Component {
  collectionName: 'components_blocks_security_spotlights';
  info: {
    description: 'Security spotlight section with 3 cards, center card emphasized';
    displayName: 'security-spotlight';
  };
  attributes: {
    anchor_id: Attribute.String;
    cards: Attribute.Component<'atoms.feature-card', true> &
      Attribute.Required &
      Attribute.SetMinMax<
        {
          min: 3;
        },
        number
      >;
    content_mode: Attribute.Enumeration<['overlay', 'side-panel']> &
      Attribute.DefaultTo<'overlay'>;
    cta: Attribute.Component<'atoms.cta-link'>;
    description: Attribute.Text;
    desktop_layout: Attribute.Enumeration<
      ['three-center-emphasis', 'three-equal']
    > &
      Attribute.DefaultTo<'three-center-emphasis'>;
    disable_overlay_in_sidepanel: Attribute.Boolean & Attribute.DefaultTo<true>;
    emphasis_index: Attribute.Integer &
      Attribute.SetMinMax<
        {
          max: 2;
          min: 0;
        },
        number
      > &
      Attribute.DefaultTo<1>;
    image_fit: Attribute.Enumeration<['contain', 'cover']> &
      Attribute.DefaultTo<'contain'>;
    infinite: Attribute.Boolean & Attribute.DefaultTo<true>;
    layout: Attribute.Enumeration<['center-emphasis', 'three-equal']> &
      Attribute.Required &
      Attribute.DefaultTo<'center-emphasis'>;
    max_width: Attribute.Enumeration<['narrow', 'default', 'wide']> &
      Attribute.DefaultTo<'default'>;
    overlay_mode: Attribute.Enumeration<['auto', 'always', 'never']> &
      Attribute.DefaultTo<'auto'>;
    overlay_style: Attribute.Enumeration<
      ['dark-gradient', 'dark-solid', 'none']
    > &
      Attribute.DefaultTo<'dark-gradient'>;
    panel_align: Attribute.Enumeration<['top', 'center']> &
      Attribute.DefaultTo<'center'>;
    panel_layout: Attribute.Enumeration<['content-left', 'content-right']> &
      Attribute.DefaultTo<'content-left'>;
    panel_width: Attribute.Enumeration<['sm', 'md', 'lg']> &
      Attribute.DefaultTo<'md'>;
    responsive_mode: Attribute.Enumeration<['carousel', 'static']> &
      Attribute.DefaultTo<'carousel'>;
    show_dots: Attribute.Boolean & Attribute.DefaultTo<true>;
    sidepanel_cta: Attribute.Component<'atoms.cta-link'>;
    sidepanel_fallback: Attribute.Component<'atoms.section-copy'>;
    sidepanel_show_dots: Attribute.Boolean & Attribute.DefaultTo<true>;
    sidepanel_use_slide_content: Attribute.Boolean & Attribute.DefaultTo<true>;
    start_position: Attribute.Enumeration<['left', 'center']> &
      Attribute.DefaultTo<'center'>;
    subtitle: Attribute.String;
    title: Attribute.String & Attribute.Required;
  };
}

export interface LinksMarketingLink extends Schema.Component {
  collectionName: 'components_links_marketing_links';
  info: {
    displayName: 'marketing.link';
  };
  attributes: {};
}

export interface LinksPrimaryCta extends Schema.Component {
  collectionName: 'components_links_primary_ctas';
  info: {
    displayName: 'primary_cta';
  };
  attributes: {};
}

export interface MarketingCta extends Schema.Component {
  collectionName: 'components_marketing_ctas';
  info: {
    displayName: 'CTA';
  };
  attributes: {
    cta: Attribute.Component<'marketing.link', true> & Attribute.Required;
    ctaHref: Attribute.String;
    ctaLabel: Attribute.String;
    description: Attribute.Text & Attribute.Required;
    subtitle: Attribute.Text;
    title: Attribute.String & Attribute.Required;
  };
}

export interface MarketingFeatureGrid extends Schema.Component {
  collectionName: 'components_marketing_feature_grids';
  info: {
    description: '';
    displayName: 'feature-grid';
  };
  attributes: {
    features: Attribute.Component<'marketing.feature-item', true>;
    items: Attribute.Component<'marketing.feature-item', true>;
    title: Attribute.String;
  };
}

export interface MarketingFeatureItem extends Schema.Component {
  collectionName: 'components_marketing_feature_items';
  info: {
    displayName: 'feature-item';
  };
  attributes: {
    description: Attribute.Text;
    icon: Attribute.Media<'images' | 'files' | 'videos' | 'audios'>;
    title: Attribute.String & Attribute.Required;
  };
}

export interface MarketingFooterSimple extends Schema.Component {
  collectionName: 'components_marketing_footer_simples';
  info: {
    displayName: 'footer-simple';
  };
  attributes: {
    copyright: Attribute.String;
    copyrightText: Attribute.String;
    links: Attribute.Component<'marketing.link', true>;
  };
}

export interface MarketingHeaderNav extends Schema.Component {
  collectionName: 'components_marketing_header_navs';
  info: {
    description: '';
    displayName: 'header-nav';
  };
  attributes: {
    cta_href: Attribute.String;
    cta_label: Attribute.String;
    cta_variant: Attribute.Enumeration<['primary', 'secondary']> &
      Attribute.DefaultTo<'primary'>;
    links: Attribute.Component<'marketing.link', true>;
    logo: Attribute.Media<'images' | 'files' | 'videos' | 'audios'>;
    logo_href: Attribute.String & Attribute.DefaultTo<'/p/home'>;
    logo_text: Attribute.String;
    primary_cta: Attribute.Component<'marketing.link'>;
    sticky: Attribute.Boolean & Attribute.DefaultTo<true>;
    theme: Attribute.Enumeration<['light', 'dark']> &
      Attribute.DefaultTo<'light'>;
    transparent_on_top: Attribute.Boolean & Attribute.DefaultTo<false>;
  };
}

export interface MarketingHero extends Schema.Component {
  collectionName: 'components_marketing_heroes';
  info: {
    description: '';
    displayName: 'hero';
  };
  attributes: {
    background_image: Attribute.Media<'images' | 'files' | 'videos' | 'audios'>;
    backgroundImage: Attribute.Media<'images' | 'files' | 'videos' | 'audios'>;
    primary_cta: Attribute.Component<'marketing.link', true>;
    primaryCtaHref: Attribute.String;
    primaryCtaLabel: Attribute.String;
    secondary_cta: Attribute.Component<'marketing.link'>;
    secondaryCtaHref: Attribute.String;
    secondaryCtaLabel: Attribute.String;
    subtitle: Attribute.String;
    title: Attribute.String & Attribute.Required;
  };
}

export interface MarketingLink extends Schema.Component {
  collectionName: 'components_marketing_links';
  info: {
    description: '';
    displayName: 'link';
  };
  attributes: {
    href: Attribute.String & Attribute.Required;
    is_external: Attribute.Boolean & Attribute.DefaultTo<false>;
    label: Attribute.String & Attribute.Required;
    variant: Attribute.Enumeration<['primary', 'secondary', 'ghost']> &
      Attribute.DefaultTo<'primary'>;
  };
}

export interface MarketingMarketingHeaderNav extends Schema.Component {
  collectionName: 'components_marketing_marketing_header_navs';
  info: {
    description: '';
    displayName: 'header-nav';
  };
  attributes: {
    links: Attribute.Component<'marketing.link', true>;
    logo: Attribute.Media<'images' | 'files' | 'videos' | 'audios'>;
    logo_text: Attribute.String;
    primary_cta: Attribute.Component<'marketing.link'>;
    sticky: Attribute.Boolean & Attribute.DefaultTo<true>;
    theme: Attribute.Enumeration<['light', 'dark']> &
      Attribute.DefaultTo<'light'>;
    transparent_on_top: Attribute.Boolean & Attribute.DefaultTo<false>;
  };
}

export interface MarketingMarketingHero extends Schema.Component {
  collectionName: 'components_marketing_marketing_heroes';
  info: {
    description: '';
    displayName: 'hero';
  };
  attributes: {
    background_image: Attribute.Media<'images' | 'files' | 'videos' | 'audios'>;
    description: Attribute.Text;
    primary_cta: Attribute.Component<'marketing.link', true>;
    secondary_cta: Attribute.Component<'marketing.link'>;
    subtitle: Attribute.String;
    title: Attribute.String & Attribute.Required;
  };
}

declare module '@strapi/types' {
  export module Shared {
    export interface Components {
      'atoms.cards-row': AtomsCardsRow;
      'atoms.cta-link': AtomsCtaLink;
      'atoms.faq-item': AtomsFaqItem;
      'atoms.feature-card': AtomsFeatureCard;
      'atoms.features-row': AtomsFeaturesRow;
      'atoms.hero-card': AtomsHeroCard;
      'atoms.partner-logo': AtomsPartnerLogo;
      'atoms.section-copy': AtomsSectionCopy;
      'blocks.ambassador-section': BlocksAmbassadorSection;
      'blocks.cards-rows': BlocksCardsRows;
      'blocks.faq-accordion': BlocksFaqAccordion;
      'blocks.feature-split': BlocksFeatureSplit;
      'blocks.features-grid': BlocksFeaturesGrid;
      'blocks.partners-strip': BlocksPartnersStrip;
      'blocks.security-spotlight': BlocksSecuritySpotlight;
      'links.marketing-link': LinksMarketingLink;
      'links.primary-cta': LinksPrimaryCta;
      'marketing.cta': MarketingCta;
      'marketing.feature-grid': MarketingFeatureGrid;
      'marketing.feature-item': MarketingFeatureItem;
      'marketing.footer-simple': MarketingFooterSimple;
      'marketing.header-nav': MarketingHeaderNav;
      'marketing.hero': MarketingHero;
      'marketing.link': MarketingLink;
      'marketing.marketing-header-nav': MarketingMarketingHeaderNav;
      'marketing.marketing-hero': MarketingMarketingHero;
    }
  }
}
