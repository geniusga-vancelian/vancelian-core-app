interface FooterLink {
  text: string;
  href: string;
}

interface FooterProps {
  logo: string;
  logo2x?: string;
  description: string;
  contact: {
    address: string;
    email: string;
    phone: string;
  };
  socialLinks: {
    twitter?: string;
    facebook?: string;
    dribbble?: string;
    instagram?: string;
    youtube?: string;
  };
  links: {
    learnMore: FooterLink[];
  };
}

export function Footer({ logo, logo2x, description, contact, socialLinks, links }: FooterProps) {
  return (
    <footer className="bg-[#343f52] text-inverse">
      <div className="container py-[4.5rem] xl:pt-20 lg:pt-20 md:pt-20">
        <div className="flex flex-wrap mx-[-15px] xl:mx-[-35px] lg:mx-[-20px] !mt-[-30px]">
          <div className="md:w-4/12 xl:w-3/12 lg:w-3/12 w-full flex-[0_0_auto] !px-[15px] max-w-full !mt-[30px]">
            <div className="widget !text-[#cacaca]">
              <img
                className="mb-4"
                src={logo}
                srcSet={logo2x ? `${logo} 1x, ${logo2x} 2x` : undefined}
                alt="Logo"
              />
              <p className="!mb-4">{description}</p>
              <nav className="nav social social-white">
                {socialLinks.twitter && (
                  <a className="!text-[#cacaca] text-[1rem] transition-all duration-[0.2s] ease-in-out translate-y-0 motion-reduce:transition-none hover:translate-y-[-0.15rem] m-[0_.7rem_0_0]" href={socialLinks.twitter}>
                    <i className="uil uil-twitter before:content-['\\ed59'] !text-white text-[1rem]"></i>
                  </a>
                )}
                {socialLinks.facebook && (
                  <a className="!text-[#cacaca] text-[1rem] transition-all duration-[0.2s] ease-in-out translate-y-0 motion-reduce:transition-none hover:translate-y-[-0.15rem] m-[0_.7rem_0_0]" href={socialLinks.facebook}>
                    <i className="uil uil-facebook-f before:content-['\\eae2'] !text-white text-[1rem]"></i>
                  </a>
                )}
                {socialLinks.dribbble && (
                  <a className="!text-[#cacaca] text-[1rem] transition-all duration-[0.2s] ease-in-out translate-y-0 motion-reduce:transition-none hover:translate-y-[-0.15rem] m-[0_.7rem_0_0]" href={socialLinks.dribbble}>
                    <i className="uil uil-dribbble before:content-['\\eaa2'] !text-white text-[1rem]"></i>
                  </a>
                )}
                {socialLinks.instagram && (
                  <a className="!text-[#cacaca] text-[1rem] transition-all duration-[0.2s] ease-in-out translate-y-0 motion-reduce:transition-none hover:translate-y-[-0.15rem] m-[0_.7rem_0_0]" href={socialLinks.instagram}>
                    <i className="uil uil-instagram before:content-['\\eb9c'] !text-white text-[1rem]"></i>
                  </a>
                )}
                {socialLinks.youtube && (
                  <a className="!text-[#cacaca] text-[1rem] transition-all duration-[0.2s] ease-in-out translate-y-0 motion-reduce:transition-none hover:translate-y-[-0.15rem] m-[0_.7rem_0_0]" href={socialLinks.youtube}>
                    <i className="uil uil-youtube before:content-['\\edb5'] !text-white text-[1rem]"></i>
                  </a>
                )}
              </nav>
            </div>
          </div>
          <div className="md:w-4/12 xl:w-3/12 lg:w-3/12 w-full flex-[0_0_auto] !px-[15px] max-w-full xl:!mt-0 lg:!mt-0 !mt-[30px]">
            <div className="widget !text-[#cacaca]">
              <h4 className="widget-title !text-white !mb-3 text-[1rem] !leading-[1.45]">Get in Touch</h4>
              <address className="xl:!pr-20 xxl:!pr-28 not-italic !leading-[inherit] block !mb-4">{contact.address}</address>
              <a className="!text-[#cacaca] hover:!text-[#fab758]" href={`mailto:${contact.email}`}>
                {contact.email}
              </a>
              <br />
              {contact.phone}
            </div>
          </div>
          <div className="md:w-4/12 xl:w-3/12 lg:w-3/12 w-full flex-[0_0_auto] !px-[15px] max-w-full xl:!mt-0 lg:!mt-0 !mt-[30px]">
            <div className="widget !text-[#cacaca]">
              <h4 className="widget-title !text-white !mb-3 text-[1rem] !leading-[1.45]">Learn More</h4>
              <ul className="pl-0 list-none !mb-0">
                {links.learnMore.map((link, index) => (
                  <li key={index} className={index > 0 ? '!mt-[0.35rem]' : ''}>
                    <a className="!text-[#cacaca] hover:!text-[#fab758]" href={link.href}>
                      {link.text}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}


