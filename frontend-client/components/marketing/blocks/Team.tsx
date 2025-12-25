interface TeamMember {
  name: string;
  role: string;
  description: string;
  image: string;
  image2x?: string;
  socialLinks: {
    twitter?: string;
    facebook?: string;
    dribbble?: string;
  };
}

interface TeamProps {
  title: string;
  heading: string;
  members: TeamMember[];
}

export function Team({ title, heading, members }: TeamProps) {
  return (
    <section className="wrapper bg-gradient-yellow">
      <div className="container py-[4.5rem] xl:pt-24 lg:pt-24 md:pt-24 xl:pb-32 lg:pb-32 md:pb-32">
        <div className="relative !mt-8 lg:!mt-[-17.5rem] xl:!mt-[-22.5rem]">
          <div className="flex flex-wrap mx-[-15px] !text-center">
            <div className="lg:w-8/12 xl:w-7/12 xxl:w-6/12 w-full flex-[0_0_auto] !px-[15px] max-w-full !mx-auto">
              <h2 className="!text-[0.8rem] !tracking-[0.02rem] uppercase !text-[#aab0bc] !mb-3 !leading-[1.35]">{title}</h2>
              <h3 className="!text-[calc(1.315rem_+_0.78vw)] font-bold xl:!text-[1.9rem] !leading-[1.25] !mb-10 md:!px-16 lg:!px-4 xl:!px-0">
                {heading}
              </h3>
            </div>
          </div>
          <div className="!relative">
            <div className="shape bg-dot blue rellax !w-[6rem] !h-[7rem] absolute opacity-50" style={{ bottom: '0.5rem', right: '-1.7rem', zIndex: 0 }}></div>
            <div className="shape !rounded-[50%] bg-line red rellax !w-[6rem] !h-[6rem] absolute opacity-50" style={{ top: '0.5rem', left: '-1.7rem', zIndex: 0 }}></div>
            <div className="flex flex-wrap mx-[-15px] grid-view !mt-[-30px] xl:!mt-0">
              {members.map((member, index) => (
                <div key={index} className="md:w-6/12 lg:w-6/12 xl:w-3/12 w-full flex-[0_0_auto] !px-[15px] max-w-full">
                  <div className="card !shadow-[0_0.25rem_1.75rem_rgba(30,34,40,0.07)]">
                    <div className="card-body p-[40px]">
                      <img
                        className="rounded-[50%] !w-[5rem] !mb-4"
                        src={member.image}
                        srcSet={member.image2x ? `${member.image} 1x, ${member.image2x} 2x` : undefined}
                        alt={member.name}
                      />
                      <h4 className="!mb-1 text-[1rem]">{member.name}</h4>
                      <div className="!text-[.7rem] uppercase !tracking-[0.02rem] font-bold !text-[#aab0bc] !mb-2">{member.role}</div>
                      <p className="!mb-2">{member.description}</p>
                      <nav className="nav social !mb-0">
                        {member.socialLinks.twitter && (
                          <a className="m-[0_.7rem_0_0] text-[1rem] transition-all duration-[0.2s] ease-in-out translate-y-0 hover:translate-y-[-0.15rem]" href={member.socialLinks.twitter}>
                            <i className="uil uil-twitter before:content-['\\ed59'] text-[1rem] !text-[#5daed5]"></i>
                          </a>
                        )}
                        {member.socialLinks.facebook && (
                          <a className="m-[0_.7rem_0_0] text-[1rem] transition-all duration-[0.2s] ease-in-out translate-y-0 hover:translate-y-[-0.15rem]" href={member.socialLinks.facebook}>
                            <i className="uil uil-facebook-f before:content-['\\eae2'] text-[1rem] !text-[#4470cf]"></i>
                          </a>
                        )}
                        {member.socialLinks.dribbble && (
                          <a className="m-[0_.7rem_0_0] text-[1rem] transition-all duration-[0.2s] ease-in-out translate-y-0 hover:translate-y-[-0.15rem]" href={member.socialLinks.dribbble}>
                            <i className="uil uil-dribbble before:content-['\\eaa2'] text-[1rem] !text-[#e94d88]"></i>
                          </a>
                        )}
                      </nav>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}


