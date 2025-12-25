import { sandboxV1Data } from '@/components/marketing/sandboxV1.data';
import { HeaderNav } from '@/components/marketing/blocks/HeaderNav';
import { Hero } from '@/components/marketing/blocks/Hero';
import { FeaturesGrid } from '@/components/marketing/blocks/FeaturesGrid';
import { SEOCheck } from '@/components/marketing/blocks/SEOCheck';
import { Steps } from '@/components/marketing/blocks/Steps';
import { Team } from '@/components/marketing/blocks/Team';
import { Solutions } from '@/components/marketing/blocks/Solutions';
import { Testimonials } from '@/components/marketing/blocks/Testimonials';
import { Footer } from '@/components/marketing/blocks/Footer';

/**
 * Sandbox V1 Marketing Page
 * 
 * Composed of reusable marketing blocks extracted from demo1.html template.
 * All blocks are React components with props, no HTML injection.
 */
export default function SandboxV1Page() {
  const { hero, features, seoCheck, steps, team, solutions, testimonials, footer } = sandboxV1Data;

  return (
    <div className="grow shrink-0 font-THICCCBOI text-[0.85rem]">
      <HeaderNav />
      <Hero {...hero} />
      <FeaturesGrid {...features} />
      <SEOCheck {...seoCheck} />
      <Steps {...steps} />
      <Team {...team} />
      <Solutions {...solutions} />
      <Testimonials {...testimonials} />
      <Footer {...footer} />
    </div>
  );
}

