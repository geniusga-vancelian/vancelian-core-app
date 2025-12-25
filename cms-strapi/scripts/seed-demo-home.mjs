import process from "node:process";
// FormData and Blob are available natively in Node.js 18+

const STRAPI_URL =
  process.env.STRAPI_INTERNAL_URL ||
  process.env.STRAPI_URL ||
  "http://localhost:1337";

// In development, try to use internal Strapi API if available (no token needed)
// In production, require STRAPI_SEED_TOKEN
const TOKEN = process.env.STRAPI_SEED_TOKEN;
const isDev = process.env.NODE_ENV !== 'production';

// In dev, we can skip token requirement if running from bootstrap
const useToken = !isDev || TOKEN;

const headers = {
  "Content-Type": "application/json",
};

if (useToken && TOKEN) {
  headers.Authorization = `Bearer ${TOKEN}`;
}

// In dev without token, we'll need to call the seed from bootstrap context
if (!isDev && !TOKEN) {
  console.error("Missing STRAPI_SEED_TOKEN in env (required in production)");
  process.exit(1);
}

async function strapiFetch(path, init = {}) {
  const url = `${STRAPI_URL}${path}`;
  const res = await fetch(url, { ...init, headers: { ...headers, ...(init.headers || {}) } });
  const text = await res.text();
  let json = null;
  try { json = text ? JSON.parse(text) : null; } catch {}
  if (!res.ok) {
    console.error("Strapi error", res.status, res.statusText, url);
    console.error(text);
    throw new Error(`Strapi request failed: ${res.status}`);
  }
  return json;
}

async function findPageIdBySlug(slug, locale) {
  const q = `/api/pages?filters[slug][$eq]=${encodeURIComponent(slug)}&locale=${encodeURIComponent(locale)}`;
  const data = await strapiFetch(q, { method: "GET" });
  const item = data?.data?.[0];
  return item?.id ?? null;
}

async function upsertPage({ slug, locale, title, seo_title, seo_description, sections }) {
  const existingId = await findPageIdBySlug(slug, locale);

  const payload = {
    data: {
      slug,
      title,
      seo_title,
      seo_description,
      sections,
    },
  };

  if (existingId) {
    console.log(`Updating page ${slug} (${locale}) id=${existingId}`);
    return strapiFetch(`/api/pages/${existingId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  }

  console.log(`Creating page ${slug} (${locale})`);
  // Crée + publie directement
  payload.data.publishedAt = new Date().toISOString();

  return strapiFetch(`/api/pages?locale=${encodeURIComponent(locale)}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


// Helper to upload placeholder logo
async function uploadPlaceholderLogo(name, index) {
  try {
    // Try to find existing images in Media Library first
    const existingImages = await strapiFetch('/api/upload/files?pagination[limit]=20&sort=createdAt:desc');
    if (existingImages?.data && existingImages.data.length > 0) {
      // Use existing image if available (cycle through them)
      const img = existingImages.data[index % existingImages.data.length];
      console.log(`[Seed] Using existing image for ${name}: ${img.name} (id: ${img.id})`);
      return img.id;
    }

    // Create SVG placeholder
    const svgContent = `<svg width="400" height="200" xmlns="http://www.w3.org/2000/svg">
      <rect width="100%" height="100%" fill="#f3f4f6"/>
      <text x="50%" y="50%" font-family="Arial, sans-serif" font-size="24" fill="#6b7280" text-anchor="middle" dominant-baseline="middle">${name}</text>
    </svg>`;
    
    // Use FormData (available in Node.js 18+)
    const formData = new FormData();
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    formData.append('files', blob, `${name.toLowerCase().replace(/\s+/g, '-')}-logo.svg`);

    // Upload via Strapi API
    const uploadResponse = await fetch(`${STRAPI_URL}/api/upload`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${TOKEN}`,
      },
      body: formData,
    });

    if (!uploadResponse.ok) {
      const text = await uploadResponse.text();
      throw new Error(`Upload failed: ${uploadResponse.status} ${text}`);
    }

    const uploadData = await uploadResponse.json();
    if (uploadData && uploadData[0] && uploadData[0].id) {
      console.log(`[Seed] Created placeholder logo for ${name} (id: ${uploadData[0].id})`);
      return uploadData[0].id;
    }

    throw new Error('Upload response missing file ID');
  } catch (error) {
    console.error(`[Seed] Failed to upload placeholder for ${name}:`, error.message);
    // Return null - the seed will skip this logo
    return null;
  }
}

async function createPartnerLogos() {
  const partnerData = [
    { name: "Partner 1", type: "technology", url: "https://example.com/partner1" },
    { name: "Partner 2", type: "financial", url: "https://example.com/partner2" },
    { name: "Partner 3", type: "media", url: "https://example.com/partner3" },
    { name: "Partner 4", type: "technology", url: "https://example.com/partner4" },
  ];

  const logos = [];
  for (let i = 0; i < partnerData.length; i++) {
    const partner = partnerData[i];
    const logoId = await uploadPlaceholderLogo(partner.name, i);
    
    // Only include logo if we have an ID
    if (logoId) {
      logos.push({
        name: partner.name,
        type: partner.type,
        logo: logoId,
        url: partner.url,
        order: i + 1,
        is_featured: i === 0, // First one is featured
      });
    }
  }

  return logos;
}

function createFaqItems() {
  return [
    {
      question: "How do I get started with investing?",
      answer: "Getting started is simple. Create an account, complete the verification process, and fund your account. Our platform guides you through each step, and our support team is available to help with any questions.",
      is_open_by_default: true,
    },
    {
      question: "What types of investments are available?",
      answer: "We offer a diverse range of investment options including stocks, ETFs, bonds, and alternative investments. All options are carefully curated and vetted to meet our quality standards.",
      is_open_by_default: false,
    },
    {
      question: "Are there any fees or minimums?",
      answer: "Our fee structure is transparent and competitive. There are no hidden fees, and minimum investment amounts vary by product. Please refer to our fee schedule for detailed information.",
      is_open_by_default: false,
    },
    {
      question: "How secure is my personal and financial information?",
      answer: "Security is our top priority. We use bank-level encryption, two-factor authentication, and follow strict regulatory compliance standards to protect your data. Your funds are held in segregated accounts with reputable custodians.",
      is_open_by_default: false,
    },
    {
      question: "Can I withdraw my funds at any time?",
      answer: "Yes, you can withdraw your available funds at any time. Processing times may vary depending on the withdrawal method and your account type. Most withdrawals are processed within 1-3 business days.",
      is_open_by_default: false,
    },
  ];
}

async function demoSections(locale) {
  const sections = [
    {
      __component: "marketing.header-nav",
      logo_text: "Sandbox",
      logo_href: "/p/home",
      theme: "light",
      sticky: true,
      links: [
        { label: locale === "fr" ? "Offres" : locale === "it" ? "Offerte" : "Offers", href: "/offers", is_external: false },
        { label: locale === "fr" ? "Partenaires" : locale === "it" ? "Partner" : "Partners", href: "/partners", is_external: false },
        { label: "Blog", href: "/blog", is_external: false },
      ],
    },
  ];

  // Add partners-strip section
  const partnerLogos = await createPartnerLogos();
  if (partnerLogos.length > 0) {
    sections.push({
      __component: "blocks.partners-strip",
      title: "Partnering with leading institutions",
      subtitle: "Media, financial and technology partners",
      partner_kind: "all",
      layout: "grid",
      theme: "light",
      show_names: false,
      grayscale: true,
      logos: partnerLogos,
    });
  } else {
    console.warn("[Seed] Skipping partners-strip: no logos available (need images in Media Library)");
  }

  // Add cards-rows section
  // Try to get images from Media Library for cards-rows
  let cardsImageIds = [];
  try {
    const existingImages = await strapiFetch('/api/upload/files?pagination[limit]=5&sort=createdAt:desc');
    if (existingImages?.data && existingImages.data.length > 0) {
      cardsImageIds = existingImages.data.slice(0, 3).map(img => img.id);
      console.log(`[Seed] Using ${cardsImageIds.length} images for cards-rows section`);
    }
  } catch (error) {
    console.warn('[Seed] Could not fetch images for cards-rows, continuing without images');
  }

  // Cards Rows Section
  if (cardsImageIds.length >= 3) {
    sections.push({
      __component: "blocks.cards-rows",
      title: "Our Solutions",
      subtitle: "Tailored offerings for every type of investor",
      rows: [
        {
          layout: "two-50-50",
          gap: 24,
          cards: [
            {
              eyebrow: "Shares App",
              title: "Retail Investors",
              description: "A user-friendly platform designed for individual investors looking to grow their wealth through accessible investment opportunities.",
              background_image: cardsImageIds[0],
              text_position: "top-left",
              cta: {
                label: "Learn more",
                href: "/shares-app",
                is_external: false,
              },
            },
            {
              eyebrow: "Shares Pro",
              title: "Wealth Managers",
              description: "Advanced tools and comprehensive solutions for professional wealth managers to serve their clients better.",
              background_image: cardsImageIds[1],
              text_position: "bottom-center",
              cta: {
                label: "Learn more",
                href: "/shares-pro",
                is_external: false,
              },
            },
          ],
        },
        {
          layout: "two-70-30",
          gap: 24,
          cards: [
            {
              eyebrow: "Shares Solutions",
              title: "Financial Institutions",
              description: "Enterprise-grade solutions and white-label options for financial institutions looking to offer investment services to their customers.",
              background_image: cardsImageIds[2],
              text_position: "center-left",
              cta: {
                label: "Learn more",
                href: "/solutions",
                is_external: false,
              },
            },
            {
              eyebrow: "Enterprise",
              title: "Custom Solutions",
              description: "Tailored to your business needs.",
              background_image: cardsImageIds[0],
              text_position: "center-center",
              cta: {
                label: "Contact us",
                href: "/contact",
                is_external: false,
              },
            },
          ],
        },
        {
          layout: "one-full",
          gap: 24,
          cards: [
            {
              eyebrow: "Get Started",
              title: "Join thousands of investors",
              description: "Start your investment journey today with our comprehensive platform.",
              background_image: cardsImageIds[1],
              text_position: "center-center",
              cta: {
                label: "Sign up now",
                href: "/signup",
                is_external: false,
              },
            },
          ],
        },
      ],
    });
  } else {
    console.warn('[Seed] Skipping cards-rows section: need at least 3 images in Media Library');
  }

  // Add feature-split sections
  // Try to get images from Media Library for feature-split
  let featureImageIds = [];
  try {
    const existingImages = await strapiFetch('/api/upload/files?pagination[limit]=3&sort=createdAt:desc');
    if (existingImages?.data && existingImages.data.length > 0) {
      featureImageIds = existingImages.data.slice(0, 2).map(img => img.id);
      console.log(`[Seed] Using ${featureImageIds.length} images for feature-split sections`);
    }
  } catch (error) {
    console.warn('[Seed] Could not fetch images for feature-split, continuing without images');
  }

  // Feature Split Section 1: "What we do?"
  if (featureImageIds.length > 0) {
    sections.push({
      __component: "blocks.feature-split",
      eyebrow: "What we do?",
      eyebrow_variant: "green",
      title: "We are building the region's leading real estate ecosystem.",
      description: "Our platform connects investors, developers, and property owners through innovative technology and seamless user experiences. We provide comprehensive tools for property management, investment tracking, and market analysis.",
      media: featureImageIds[0],
      layout: "image_right",
      cta: {
        label: "Learn more",
        href: "/about-us",
        is_external: false,
      },
    });
  } else {
    console.warn('[Seed] Skipping feature-split section 1: no images available');
  }

  // Feature Split Section 2: "Why we do it?"
  if (featureImageIds.length > 1) {
    sections.push({
      __component: "blocks.feature-split",
      eyebrow: "Why we do it?",
      eyebrow_variant: "purple",
      title: "We enable Real Estate Freedom for everyone.",
      description: "We believe that real estate investment should be accessible, transparent, and empowering. Our mission is to democratize access to property markets and help individuals build wealth through real estate.",
      media: featureImageIds[1],
      layout: "image_left",
      cta: {
        label: "Learn more",
        href: "/about-us",
        is_external: false,
      },
    });
  } else if (featureImageIds.length === 1) {
    // Use the same image if only one is available
    sections.push({
      __component: "blocks.feature-split",
      eyebrow: "Why we do it?",
      eyebrow_variant: "purple",
      title: "We enable Real Estate Freedom for everyone.",
      description: "We believe that real estate investment should be accessible, transparent, and empowering. Our mission is to democratize access to property markets and help individuals build wealth through real estate.",
      media: featureImageIds[0],
      layout: "image_left",
      cta: {
        label: "Learn more",
        href: "/about-us",
        is_external: false,
      },
    });
  } else {
    console.warn('[Seed] Skipping feature-split section 2: no images available');
  }

  // Add FAQ accordion section
  const faqItems = createFaqItems();
  sections.push({
    __component: "blocks.faq-accordion",
    eyebrow: "FREQUENTLY ASKED QUESTIONS",
    title: "FAQs",
    items: faqItems,
  });

  // Add ambassador section
  // Try to attach a background image from Media Library if available
  let backgroundImageId = null;
  try {
    const existingImages = await strapiFetch('/api/upload/files?pagination[limit]=1&sort=createdAt:desc');
    if (existingImages?.data && existingImages.data.length > 0) {
      backgroundImageId = existingImages.data[0].id;
      console.log(`[Seed] Using background image for ambassador section: ${existingImages.data[0].name} (id: ${backgroundImageId})`);
    }
  } catch (error) {
    console.warn('[Seed] Could not fetch images for ambassador section background, continuing without image');
  }

  const ambassadorSection = {
    __component: "blocks.ambassador-section",
    title: "Supported by the best",
    subtitle: "Champions in partnership",
    card_title: "Partner with a winning team",
    card_text: "Just like Shares advocates Venus and Serena, we believe in the power of partnership.",
    cta: {
      label: "About us",
      href: "/about-us",
      is_external: false,
    },
    overlay_opacity: 35, // 0.35 as integer (0-85 range)
    card_height: "lg",
    content_max_width: "md",
    align: "left",
  };

  // Only add background_image if we found one
  if (backgroundImageId) {
    ambassadorSection.background_image = backgroundImageId;
  }

  sections.push(ambassadorSection);

  // Add security-spotlight section
  sections.push({
    __component: "blocks.security-spotlight",
    title: "Your money, protected",
    subtitle: "Advanced security features",
    description: "We use industry-leading security measures to keep your finances safe. Our multi-layered protection ensures your assets are always secure.",
    cta: {
      label: "Learn more",
      href: "/security",
      is_external: false,
    },
    layout: "center-emphasis",
    max_width: "default",
    start_position: "center",
    overlay_mode: "auto",
    overlay_style: "dark-gradient",
    emphasis_index: 1,
    cards: [
      {
        title: "Freeze and unfreeze in seconds",
        text: "Take control of your cards instantly. Freeze any card with a tap if it's lost or stolen, and unfreeze it just as quickly when you find it.",
        card_theme: "muted",
        accent: "brand",
      },
      {
        title: "Algorithms that spot suspicious activity",
        text: "Our advanced machine learning systems continuously monitor your account for unusual patterns. Get instant alerts for any suspicious transactions and approve or decline them in real-time.",
        card_theme: "dark",
        accent: "success",
      },
      {
        title: "Biometric security for withdrawals",
        text: "Protect your account with fingerprint or face recognition. Every sensitive action requires biometric authentication, adding an extra layer of security to your transactions.",
        card_theme: "muted",
        accent: "brand",
      },
    ],
  });

  // Add features-grid section
  sections.push({
    __component: "blocks.features-grid",
    title: "Everything you need, in one spot",
    subtitle: "Powerful tools and features designed for modern investors",
    cta: {
      label: "Get started",
      href: "/get-started",
      is_external: false,
    },
    rows: [
      {
        columns: "three",
        cards: [
          {
            eyebrow: "Investing",
            title: "Diverse investment options",
            text: "Access a wide range of investment products including stocks, ETFs, bonds, and alternative investments. Build a diversified portfolio tailored to your risk tolerance and financial goals.",
            bullet_type: "icon",
            icon: "coins",
            card_theme: "muted",
            accent: "brand",
          },
          {
            eyebrow: "Global",
            title: "International markets",
            text: "Invest in markets worldwide with our global platform. Access US, European, and Asian markets all from a single account with competitive fees and transparent pricing.",
            bullet_type: "icon",
            icon: "globe",
            card_theme: "muted",
            accent: "brand",
          },
          {
            eyebrow: "Integration",
            title: "Seamless connections",
            text: "Connect your existing accounts and financial tools. Import transactions, sync with banking apps, and integrate with popular financial planning software.",
            bullet_type: "icon",
            icon: "link",
            card_theme: "muted",
            accent: "brand",
          },
        ],
      },
      {
        columns: "three",
        cards: [
          {
            eyebrow: "Analytics",
            title: "Advanced analytics",
            text: "Track your portfolio performance with real-time analytics and comprehensive reporting. Understand your asset allocation, risk exposure, and investment returns.",
            bullet_type: "icon",
            icon: "bar-chart-3",
            card_theme: "muted",
            accent: "info",
          },
          {
            eyebrow: "Security",
            title: "Bank-level security",
            text: "Your investments are protected with enterprise-grade security. Multi-factor authentication, encryption, and regular security audits ensure your assets are safe.",
            bullet_type: "icon",
            icon: "shield",
            card_theme: "muted",
            accent: "success",
          },
          {
            eyebrow: "Support",
            title: "Expert guidance",
            text: "Get help from our team of financial advisors and customer support specialists. Access educational resources, investment guides, and personalized recommendations.",
            bullet_type: "icon",
            icon: "help-circle",
            card_theme: "muted",
            accent: "brand",
          },
        ],
      },
    ],
  });

  // Add second features-grid section with numbered bullets (like "Switch in 3 Steps")
  sections.push({
    __component: "blocks.features-grid",
    title: "Switch to Vancelian in 3 Steps",
    subtitle: "Get started in minutes with our simple onboarding process",
    cta: {
      label: "Join Vancelian",
      href: "/signup",
      is_external: false,
    },
    rows: [
      {
        columns: "three",
        cards: [
          {
            title: "Open an account",
            text: "Create your account in minutes with our streamlined signup process. Verify your identity and link your bank account to get started.",
            bullet_type: "number",
            number: 1,
            card_theme: "light",
            accent: "brand",
          },
          {
            title: "Switch your payments",
            text: "Move any recurring payments, subscriptions, and utility bills from your other accounts to Vancelian. Set up automatic transfers and never miss a payment.",
            bullet_type: "number",
            number: 2,
            card_theme: "light",
            accent: "brand",
          },
          {
            title: "Automate your finances",
            text: "Set up automatic savings, investment contributions, and budget allocations. Let Vancelian handle your financial routine so you can focus on what matters.",
            bullet_type: "number",
            number: 3,
            card_theme: "light",
            accent: "brand",
          },
        ],
      },
    ],
  });

  return sections;
}

async function main() {
  const slug = "home";

  // Only seed 'en' locale for now
  const locale = "en";
  const title = "Home";
  
  const sections = await demoSections(locale);
  
  await upsertPage({
    slug,
    locale,
    title,
    seo_title: title,
    seo_description: "Sandbox demo page with header navigation and partners strip.",
    sections,
  });

  console.log("✅ Demo Home seeded (locale=en).");
  console.log(`   Sections: ${sections.map(s => s.__component).join(', ')}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

