'use strict';

/**
 * Page lifecycle hooks
 * Normalizes data in sections to prevent inconsistencies
 */

// Default icon to use if bullet_type=icon but icon is missing
const DEFAULT_ICON = 'sparkles';

// Icon name mapping: enum value -> Lucide component name
const ICON_NAME_MAP = {
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

/**
 * Normalize feature card data based on bullet_type
 */
function normalizeFeatureCard(card, index) {
  if (!card || typeof card !== 'object') {
    return card;
  }

  const bulletType = card.bullet_type;

  if (bulletType === 'icon') {
    // If icon type, normalize icon enum and clear number
    let iconEnumValue = card.icon;
    
    // If bullet_value exists but icon doesn't, try to reverse map
    if (!iconEnumValue && card.bullet_value) {
      // Reverse lookup: find enum key by Lucide component name
      iconEnumValue = Object.keys(ICON_NAME_MAP).find(key => 
        ICON_NAME_MAP[key] === card.bullet_value
      ) || DEFAULT_ICON;
    }
    
    iconEnumValue = iconEnumValue || DEFAULT_ICON;
    
    // Convert icon enum to Lucide component name for bullet_value
    const lucideComponentName = ICON_NAME_MAP[iconEnumValue.toLowerCase()] || 'Sparkles';
    
    return {
      ...card,
      bullet_type: 'icon',
      bullet_value: lucideComponentName, // Store Lucide component name for frontend
      icon: iconEnumValue, // Keep enum value for Strapi
      number: null, // Clear number
    };
  } else if (bulletType === 'number') {
    // If number type, normalize number and clear icon
    const numberValue = card.number || (card.bullet_value ? parseInt(card.bullet_value, 10) : null) || (index + 1);
    
    return {
      ...card,
      bullet_type: 'number',
      bullet_value: String(numberValue), // Store as string for frontend
      number: typeof numberValue === 'number' ? numberValue : parseInt(String(numberValue), 10) || (index + 1),
      icon: null, // Clear icon enum
    };
  }

  // If bullet_type is not set, default to icon
  return {
    ...card,
    bullet_type: card.bullet_type || 'icon',
    icon: card.icon || DEFAULT_ICON,
    bullet_value: card.bullet_value || ICON_NAME_MAP[DEFAULT_ICON] || 'Sparkles',
    number: null,
  };
}

/**
 * Normalize cards in a section
 */
function normalizeSectionCards(section) {
  if (!section || typeof section !== 'object') {
    return section;
  }

  // Check if this section has cards that need normalization
  // This includes: features-grid rows, security-spotlight cards, etc.
  
  const componentType = section.__component || '';

  // Handle features-grid: normalize cards in rows
  if (componentType === 'blocks.features-grid' && Array.isArray(section.rows)) {
    return {
      ...section,
      rows: section.rows.map(row => ({
        ...row,
        cards: Array.isArray(row.cards)
          ? row.cards.map((card, index) => normalizeFeatureCard(card, index))
          : row.cards,
      })),
    };
  }

  // Handle security-spotlight: normalize cards directly
  if (componentType === 'blocks.security-spotlight' && Array.isArray(section.cards)) {
    return {
      ...section,
      cards: section.cards.map((card, index) => normalizeFeatureCard(card, index)),
    };
  }

  return section;
}

module.exports = {
  async beforeCreate(event) {
    const { data } = event.params;

    if (data && Array.isArray(data.sections)) {
      data.sections = data.sections.map(normalizeSectionCards);
    }
  },

  async beforeUpdate(event) {
    const { data } = event.params;

    if (data && Array.isArray(data.sections)) {
      data.sections = data.sections.map(normalizeSectionCards);
    }
  },
};
