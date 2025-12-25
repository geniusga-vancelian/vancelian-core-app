/**
 * Footer Simple Block - Renders a simple footer from Strapi CMS
 * Used in Dynamic Zone sections
 */

import Link from 'next/link';

export interface FooterLink {
  label: string;
  href: string;
  is_external?: boolean;
}

export interface FooterSimpleBlockProps {
  copyrightText?: string;
  links?: FooterLink[];
}

export function FooterSimpleBlock({
  copyrightText,
  links = [],
}: FooterSimpleBlockProps) {
  return (
    <footer className="py-12 bg-gray-900 text-white">
      <div className="container mx-auto px-4">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          {copyrightText && (
            <p className="text-gray-400 text-sm">
              {copyrightText}
            </p>
          )}
          
          {links.length > 0 && (
            <nav className="flex flex-wrap gap-6">
              {links.map((link, index) => {
                // Use <a> for external links, Link for internal
                const isExternal = link.is_external || link.href.startsWith('http');
                
                if (isExternal) {
                  return (
                    <a
                      key={index}
                      href={link.href}
                      className="text-gray-400 hover:text-white text-sm transition-colors"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {link.label}
                    </a>
                  );
                }
                
                return (
                  <Link
                    key={index}
                    href={link.href}
                    className="text-gray-400 hover:text-white text-sm transition-colors"
                  >
                    {link.label}
                  </Link>
                );
              })}
            </nav>
          )}
        </div>
      </div>
    </footer>
  );
}


