'use client';

import { useState, useEffect } from 'react';

/**
 * HeaderNav Component - Navigation header based on Sandbox template demo1.html
 * Includes fallback React menu for mobile if template JS is not loaded
 */
export function HeaderNav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [jsLoaded, setJsLoaded] = useState(false);

  // Check if template JS is loaded (Bootstrap/theme.js)
  useEffect(() => {
    // Check if Bootstrap is available (loaded by plugins.js/theme.js)
    if (typeof window !== 'undefined') {
      const checkJs = () => {
        // @ts-ignore - Bootstrap might be loaded from template JS
        const hasBootstrap = typeof window.bootstrap !== 'undefined';
        setJsLoaded(hasBootstrap);
      };
      
      // Check immediately and after a delay (scripts might load async)
      checkJs();
      const timer = setTimeout(checkJs, 1000);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleDropdownClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (!jsLoaded) {
      e.preventDefault();
      const dropdown = e.currentTarget.nextElementSibling as HTMLElement;
      if (dropdown) {
        dropdown.classList.toggle('hidden');
      }
    }
  };

  return (
    <header className="relative wrapper !bg-[#fff8ee] z-[9999]">
      <nav className="navbar navbar-expand-lg center-nav transparent navbar-light">
        <div className="container xl:!flex-row lg:!flex-row !flex-nowrap items-center">
          <div className="navbar-brand w-full">
            <a href="/">
              <img
                src="/theme/assets/img/logo-dark.png"
                srcSet="/theme/assets/img/logo-dark@2x.png 2x"
                alt="Logo"
              />
            </a>
          </div>
          
          {/* Desktop Navigation - Visible on xl/lg, uses offcanvas structure but displayed inline */}
          <div className="navbar-collapse offcanvas offcanvas-nav offcanvas-start">
            <div className="offcanvas-header xl:!hidden lg:!hidden flex items-center justify-between flex-row p-6">
              <h3 className="!text-white xl:!text-[1.5rem] !text-[calc(1.275rem_+_0.3vw)] !mb-0">Sandbox</h3>
              <button 
                type="button"
                className="btn-close btn-close-white !mr-[-0.75rem] m-0 p-0 leading-none !text-[#343f52] transition-all duration-[0.2s] ease-in-out border-0 motion-reduce:transition-none before:text-[1.05rem] before:text-white before:content-['\\ed3b'] before:w-[1.8rem] before:h-[1.8rem] before:leading-[1.8rem] before:shadow-none before:transition-[background] before:duration-[0.2s] before:ease-in-out before:!flex before:justify-center before:items-center before:m-0 before:p-0 before:rounded-[100%] hover:no-underline bg-inherit before:bg-[rgba(255,255,255,.08)] before:font-Unicons hover:before:bg-[rgba(0,0,0,.11)]"
                data-bs-dismiss="offcanvas"
                aria-label="Close"
                onClick={() => setMobileMenuOpen(false)}
              ></button>
            </div>
            <div className="offcanvas-body xl:!ml-auto lg:!ml-auto xl:!flex lg:!flex xl:!flex-row lg:!flex-row !flex-col !h-full">
              <ul className="navbar-nav xl:!flex-row lg:!flex-row">
                <li className="nav-item dropdown dropdown-mega group">
                  <a
                    className="nav-link dropdown-toggle !text-[.85rem] after:!text-[#fab758] group-hover:!text-[#fab758]"
                    href="#"
                    data-bs-toggle={jsLoaded ? 'dropdown' : undefined}
                    onClick={handleDropdownClick}
                  >
                    Demos
                  </a>
                  <ul className={`dropdown-menu mega-menu mega-menu-dark mega-menu-img ${!jsLoaded ? 'hidden' : ''}`}>
                    <li className="mega-menu-content mega-menu-scroll">
                      <ul className="grid grid-cols-1 xl:grid-cols-6 lg:grid-cols-6 mx-0 xl:mx-[-10px] lg:mx-[-10px] xl:!mt-[-10px] lg:!mt-[-10px] !pl-0 list-none">
                        <li className="xl:!px-[10px] xl:!mt-[10px] lg:!px-[10px] lg:!mt-[10px]">
                          <a className="dropdown-item" href="/theme-preview?file=demo1.html">
                            <span className="xl:!hidden lg:!hidden">Demo 1</span>
                          </a>
                        </li>
                      </ul>
                    </li>
                  </ul>
                </li>
                <li className="nav-item dropdown group">
                  <a
                    className="nav-link dropdown-toggle !text-[.85rem] after:!text-[#fab758] group-hover:!text-[#fab758]"
                    href="#"
                    data-bs-toggle={jsLoaded ? 'dropdown' : undefined}
                    onClick={handleDropdownClick}
                  >
                    Pages
                  </a>
                  <ul className={`dropdown-menu ${!jsLoaded ? 'hidden' : ''}`}>
                    <li className="nav-item">
                      <a className="dropdown-item hover:!text-[#fab758]" href="/offers">
                        Offers
                      </a>
                    </li>
                    <li className="nav-item">
                      <a className="dropdown-item hover:!text-[#fab758]" href="/partners">
                        Partners
                      </a>
                    </li>
                    <li className="nav-item">
                      <a className="dropdown-item hover:!text-[#fab758]" href="/blog">
                        Blog
                      </a>
                    </li>
                  </ul>
                </li>
                <li className="nav-item dropdown group">
                  <a
                    className="nav-link dropdown-toggle !text-[.85rem] after:!text-[#fab758] group-hover:!text-[#fab758]"
                    href="#"
                    data-bs-toggle={jsLoaded ? 'dropdown' : undefined}
                    onClick={handleDropdownClick}
                  >
                    Projects
                  </a>
                </li>
                <li className="nav-item dropdown group">
                  <a
                    className="nav-link dropdown-toggle !text-[.85rem] after:!text-[#fab758] group-hover:!text-[#fab758]"
                    href="#"
                    data-bs-toggle={jsLoaded ? 'dropdown' : undefined}
                    onClick={handleDropdownClick}
                  >
                    Blog
                  </a>
                </li>
                <li className="nav-item dropdown dropdown-mega group">
                  <a
                    className="nav-link dropdown-toggle !text-[.85rem] after:!text-[#fab758] group-hover:!text-[#fab758]"
                    href="#"
                    data-bs-toggle={jsLoaded ? 'dropdown' : undefined}
                    onClick={handleDropdownClick}
                  >
                    Blocks
                  </a>
                </li>
                <li className="nav-item dropdown dropdown-mega group">
                  <a
                    className="nav-link dropdown-toggle !text-[.85rem] after:!text-[#fab758] group-hover:!text-[#fab758]"
                    href="#"
                    data-bs-toggle={jsLoaded ? 'dropdown' : undefined}
                    onClick={handleDropdownClick}
                  >
                    Documentation
                  </a>
                </li>
              </ul>
            </div>
          </div>

          {/* Right side: Language selector, Info button, Mobile menu button */}
          <div className="navbar-other w-full !flex !ml-auto">
            <ul className="navbar-nav !flex-row !items-center !ml-auto">
              {/* Language selector - Desktop only */}
              <li className="nav-item dropdown language-select uppercase group hidden xl:!block lg:!block">
                <a
                  className="nav-link dropdown-item dropdown-toggle after:!text-[#fab758] xl:!text-[.85rem] lg:!text-[.85rem] md:!text-[1.05rem] max-md:!text-[1.05rem] hover:!text-[#fab758]"
                  href="#"
                  role="button"
                  data-bs-toggle={jsLoaded ? 'dropdown' : undefined}
                  aria-haspopup="true"
                  aria-expanded="false"
                  onClick={handleDropdownClick}
                >
                  En
                </a>
                <ul className={`dropdown-menu group-hover:shadow-[0_0.25rem_0.75rem_rgba(30,34,40,0.15)] ${!jsLoaded ? 'hidden' : ''}`}>
                  <li className="nav-item">
                    <a className="dropdown-item hover:!text-[#fab758] hover:bg-[inherit]" href="#">
                      En
                    </a>
                  </li>
                  <li className="nav-item">
                    <a className="dropdown-item hover:!text-[#fab758] hover:bg-[inherit]" href="#">
                      De
                    </a>
                  </li>
                  <li className="nav-item">
                    <a className="dropdown-item hover:!text-[#fab758] hover:bg-[inherit]" href="#">
                      Es
                    </a>
                  </li>
                </ul>
              </li>
              {/* Info button - Desktop only */}
              <li className="nav-item hidden xl:!block lg:!block">
                <a
                  className="nav-link hover:!text-[#fab758]"
                  data-bs-toggle={jsLoaded ? 'offcanvas' : undefined}
                  data-bs-target={jsLoaded ? '#offcanvas-info' : undefined}
                  href="#"
                >
                  <i className="uil uil-info-circle before:content-['\\eb99'] !text-[1.1rem]"></i>
                </a>
              </li>
              {/* Mobile menu button */}
              <li className="nav-item xl:!hidden lg:!hidden">
                <button
                  className="hamburger offcanvas-nav-btn"
                  onClick={(e) => {
                    e.preventDefault();
                    if (!jsLoaded) {
                      // React fallback: toggle mobile menu
                      setMobileMenuOpen(!mobileMenuOpen);
                    }
                    // If JS is loaded, let template JS handle it via data-bs-toggle
                  }}
                  data-bs-toggle={jsLoaded ? 'offcanvas' : undefined}
                  data-bs-target={jsLoaded ? '.offcanvas-nav' : undefined}
                  aria-label="Toggle navigation"
                >
                  <span></span>
                </button>
              </li>
            </ul>
          </div>
        </div>
      </nav>

      {/* React Fallback Mobile Menu (only if JS not loaded) */}
      {!jsLoaded && mobileMenuOpen && (
        <div className="xl:hidden lg:hidden fixed inset-0 z-[10000] bg-[#343f52] text-white">
          <div className="p-6">
            <div className="flex justify-between items-center mb-8">
              <h3 className="text-xl font-bold">Menu</h3>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="text-white text-2xl"
                aria-label="Close menu"
              >
                ×
              </button>
            </div>
            <ul className="space-y-4">
              <li>
                <a href="/sandbox-v1" className="text-white hover:text-[#fab758] block py-2" onClick={() => setMobileMenuOpen(false)}>
                  Home
                </a>
              </li>
              <li>
                <a href="/offers" className="text-white hover:text-[#fab758] block py-2" onClick={() => setMobileMenuOpen(false)}>
                  Offers
                </a>
              </li>
              <li>
                <a href="/partners" className="text-white hover:text-[#fab758] block py-2" onClick={() => setMobileMenuOpen(false)}>
                  Partners
                </a>
              </li>
              <li>
                <a href="/blog" className="text-white hover:text-[#fab758] block py-2" onClick={() => setMobileMenuOpen(false)}>
                  Blog
                </a>
              </li>
            </ul>
          </div>
        </div>
      )}
    </header>
  );
}
