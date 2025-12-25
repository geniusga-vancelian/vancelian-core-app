interface TestimonialItem {
  quote: string;
  author: string;
  role: string;
}

interface TestimonialsProps {
  title: string;
  heading: string;
  description: string;
  ctaText: string;
  ctaLink: string;
  items: TestimonialItem[];
}

export function Testimonials({ title, heading, description, ctaText, ctaLink, items }: TestimonialsProps) {
  return (
    <section className="wrapper bg-gradient-reverse-primary">
      <div className="container py-[4.5rem] xl:!py-[8rem] lg:!py-[8rem] md:!py-[8rem]">
        <div className="flex flex-wrap mx-[-15px] xl:mx-[-35px] lg:mx-[-20px] !mt-[-50px] items-center">
          <div className="xl:w-7/12 lg:w-7/12 w-full flex-[0_0_auto] xl:!px-[35px] lg:!px-[20px] !px-[15px] !mt-[50px] max-w-full">
            <div className="flex flex-wrap mx-[-15px] xl:mx-[-12.5px] lg:mx-[-12.5px] md:mx-[-12.5px] !mt-[-25px]">
              {items.map((item, index) => (
                <div
                  key={index}
                  className={`md:w-6/12 lg:w-6/12 ${index === 0 ? 'xl:w-5/12' : 'xl:w-6/12'} w-full flex-[0_0_auto] !px-[15px] xl:!px-[12.5px] lg:!px-[12.5px] md:!px-[12.5px] !mt-[25px] max-w-full !self-end`}
                >
                  <div className="card !shadow-[0_0.25rem_1.75rem_rgba(30,34,40,0.07)]">
                    <div className="card-body flex-[1_1_auto] p-[40px]">
                      <blockquote className="!text-[.9rem] !leading-[1.7] font-medium !pl-4 icon !mb-0 relative p-0 border-0 before:content-['\u201d'] before:absolute before:top-[-1.5rem] before:left-[-0.9rem] before:text-[rgba(52,63,82,0.05)] before:text-[10rem] before:leading-none before:z-[1]">
                        <p>"{item.quote}"</p>
                        <div className="flex items-center text-left">
                          <div className="info p-0">
                            <h5 className="!mb-1 text-[.95rem] !leading-[1.5]">{item.author}</h5>
                            <p className="!mb-0 !text-[.85rem]">{item.role}</p>
                          </div>
                        </div>
                      </blockquote>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="xl:w-5/12 lg:w-5/12 w-full flex-[0_0_auto] xl:!px-[35px] lg:!px-[20px] !px-[15px] !mt-[50px] max-w-full">
            <h2 className="!text-[0.8rem] !tracking-[0.02rem] !leading-[1.35] uppercase !text-[#aab0bc] !mb-3 xl:!mt-[-1.5rem] lg:!mt-[-1.5rem]">
              {title}
            </h2>
            <h3 className="!text-[calc(1.315rem_+_0.78vw)] font-bold xl:!text-[1.9rem] !leading-[1.25] !mb-5">{heading}</h3>
            <p>{description}</p>
            <a
              href={ctaLink}
              className="btn btn-yellow !text-white !bg-[#fab758] border-[#fab758] hover:text-white hover:bg-[#fab758] hover:!border-[#fab758] active:text-white active:bg-[#fab758] active:border-[#fab758] disabled:text-white disabled:bg-[#fab758] disabled:border-[#fab758] !text-[.85rem] !rounded-[50rem] !mt-3 hover:translate-y-[-0.15rem] hover:shadow-[0_0.25rem_0.75rem_rgba(30,34,40,0.15)]"
            >
              {ctaText}
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

