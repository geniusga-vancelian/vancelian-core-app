/**
 * Demo20 Page - React version of demo20.html template
 * Assembles Sandbox template components
 */

'use client';

import { useEffect } from 'react';
import { HeaderNav } from '@/components/sandbox/demo20/HeaderNav';
import { HeroVideo } from '@/components/sandbox/demo20/HeroVideo';
import { SectionServices } from '@/components/sandbox/demo20/SectionServices';
import { SectionProcess } from '@/components/sandbox/demo20/SectionProcess';
import { SectionProjects } from '@/components/sandbox/demo20/SectionProjects';
import { SectionClients } from '@/components/sandbox/demo20/SectionClients';
import { SectionCTA } from '@/components/sandbox/demo20/SectionCTA';
import { Footer } from '@/components/sandbox/demo20/Footer';

/**
 * Demo20 Page Component
 * Ensures theme JS is initialized properly after mount
 */
export default function Demo20Page() {
  useEffect(() => {
    // Guard against double initialization
    if (typeof window === 'undefined') return;
    
    const initKey = '__demo20_theme_inited';
    if ((window as any)[initKey]) {
      return; // Already initialized
    }

    // Wait for scripts to load, then initialize theme if needed
    const initTheme = () => {
      // Check if theme.init exists and call it
      if ((window as any).theme && typeof (window as any).theme.init === 'function') {
        try {
          (window as any).theme.init();
          (window as any)[initKey] = true;
        } catch (error) {
          console.error('[Demo20] Error initializing theme:', error);
        }
      }
    };

    // Try immediately
    initTheme();

    // Also try after a short delay (scripts might still be loading)
    const timeout = setTimeout(initTheme, 500);

    return () => {
      clearTimeout(timeout);
    };
  }, []);

  return (
    <>
      <header className="relative wrapper">
        <HeaderNav />
      </header>

      <HeroVideo />

      <SectionServices />

      <SectionProcess />

      <SectionProjects />

      <SectionClients />

      <SectionCTA />

      <Footer />

      {/* Progress wrapper (scroll to top button) */}
      <div className="progress-wrap fixed w-[2.3rem] h-[2.3rem] cursor-pointer block shadow-[inset_0_0_0_0.1rem_rgba(128,130,134,0.25)] z-[1010] opacity-0 invisible translate-y-3 transition-all duration-[0.2s] ease-[linear,margin-right] delay-[0s] rounded-[100%] right-6 bottom-6 motion-reduce:transition-none after:absolute after:content-['\e951'] after:text-center after:leading-[2.3rem] after:text-[1.2rem] after:!text-[#605dba] after:h-[2.3rem] after:w-[2.3rem] after:cursor-pointer after:block after:z-[1] after:transition-all after:duration-[0.2s] after:ease-linear after:left-0 after:top-0 motion-reduce:after:transition-none after:font-Unicons">
        <svg className="progress-circle svg-content" width="100%" height="100%" viewBox="-1 -1 102 102">
          <path className="fill-none stroke-[#605dba] stroke-[4] box-border transition-all duration-[0.2s] ease-linear motion-reduce:transition-none" d="M50,1 a49,49 0 0,1 0,98 a49,49 0 0,1 0,-98" />
        </svg>
      </div>
    </>
  );
}


