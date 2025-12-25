interface StepItem {
  number: string;
  title: string;
  description: string;
}

interface StepsProps {
  title: string;
  heading: string;
  description: string;
  description2: string;
  ctaText: string;
  ctaLink: string;
  items: StepItem[];
  image: string;
  image2x?: string;
}

export function Steps({ title, heading, description, description2, ctaText, ctaLink, items, image, image2x }: StepsProps) {
  return (
    <section className="wrapper !bg-[#ffffff] angled upper-start lower-start relative border-0 before:top-[-4rem] before:content-[''] before:block before:absolute before:z-0 before:border-l-[100vw] before:border-r-transparent before:border-t-[4rem] before:border-y-transparent before:border-[#fefefe] before:border-0 before:border-solid before:right-0 after:bottom-[-4rem] after:content-[''] after:block after:absolute after:z-0 after:border-l-[100vw] after:border-r-transparent after:border-b-[4rem] after:border-y-transparent after:border-[#fefefe] after:border-0 after:border-solid after:right-0">
      <div className="container py-[4.5rem] xl:pt-28 lg:pt-28 md:pt-28 xl:pb-20 lg:pb-20 md:pb-20">
        <div className="flex flex-wrap mx-[-15px] xl:mx-[-35px] lg:mx-[-20px] md:mx-[-20px] !mt-[-50px] !mb-[4.5rem] xl:!mb-[8rem] lg:!mb-[8rem] md:!mb-[8rem] items-center">
          <div className="xl:w-6/12 lg:w-6/12 w-full flex-[0_0_auto] !px-[15px] max-w-full xl:!order-2 lg:!order-2 xl:!px-[35px] lg:!px-[20px] md:!px-[20px] !mt-[50px]">
            {items.map((item, index) => (
              <div key={index} className={`card ${index === 0 ? 'xl:!mr-6 lg:!mr-6' : index === 1 ? '!mt-6 xl:!ml-16 lg:!ml-16' : '!mt-6 xl:mx-6 lg:mx-6'} !shadow-[0_0.25rem_1.75rem_rgba(30,34,40,0.07)]`}>
                <div className="card-body p-6">
                  <div className="flex flex-row">
                    <div>
                      <span className="icon btn btn-circle btn-lg btn-soft-yellow pointer-events-none !mr-4 xl:!text-[1.3rem] !w-12 !h-12 !text-[calc(1.255rem_+_0.06vw)] inline-flex items-center justify-center leading-none !p-0 !rounded-[100%]">
                        <span className="number table-cell text-center align-middle text-[1.1rem] font-bold m-[0_auto]">{item.number}</span>
                      </span>
                    </div>
                    <div>
                      <h4 className="!mb-1 text-[1rem]">{item.title}</h4>
                      <p className="!mb-0">{item.description}</p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="xl:w-6/12 lg:w-6/12 w-full flex-[0_0_auto] !px-[15px] max-w-full xl:!px-[35px] lg:!px-[20px] md:!px-[20px] !mt-[50px]">
            <h2 className="!text-[0.8rem] !tracking-[0.02rem] uppercase !text-[#aab0bc] !mb-3 !leading-[1.35]">{title}</h2>
            <h3 className="!text-[calc(1.315rem_+_0.78vw)] font-bold xl:!text-[1.9rem] !leading-[1.25] !mb-5">{heading}</h3>
            <p>{description}</p>
            <p className="!mb-6">{description2}</p>
            <a
              href={ctaLink}
              className="btn btn-yellow !text-white !bg-[#fab758] border-[#fab758] hover:text-white hover:bg-[#fab758] hover:!border-[#fab758] active:text-white active:bg-[#fab758] active:border-[#fab758] disabled:text-white disabled:bg-[#fab758] disabled:border-[#fab758] !text-[.85rem] !rounded-[50rem] !mb-0 hover:translate-y-[-0.15rem] hover:shadow-[0_0.25rem_0.75rem_rgba(30,34,40,0.15)]"
            >
              {ctaText}
            </a>
          </div>
        </div>
        <div className="flex flex-wrap mx-[-15px] xl:mx-[-35px] lg:mx-[-20px] !mt-[-50px] lg:!mb-60 xl:!mb-80 items-center">
          <div className="xl:w-7/12 lg:w-7/12 w-full flex-[0_0_auto] xl:!px-[35px] lg:!px-[20px] !px-[15px] !mt-[50px] max-w-full">
            <figure className="m-0 p-0">
              <img
                className="w-auto"
                src={image}
                srcSet={image2x ? `${image} 1x, ${image2x} 2x` : undefined}
                alt="Steps illustration"
              />
            </figure>
          </div>
          <div className="xl:w-5/12 lg:w-5/12 w-full flex-[0_0_auto] xl:!px-[35px] lg:!px-[20px] !px-[15px] !mt-[50px] max-w-full">
            <h2 className="!text-[0.8rem] !tracking-[0.02rem] uppercase !text-[#aab0bc] !mb-3 !leading-[1.35]">Why Choose Us?</h2>
            <h3 className="!text-[calc(1.315rem_+_0.78vw)] !leading-[1.25] font-bold xl:!text-[1.9rem] !mb-7">
              We bring solutions to make life easier for our clients.
            </h3>
            {/* FAQ Accordion - simplified for V1 */}
            <div className="space-y-4">
              <details className="card plain">
                <summary className="accordion-button !text-[0.9rem] before:!text-[#fab758] hover:!text-[#fab758] cursor-pointer card-header !mb-0 !p-[0_0_.8rem_0] !border-0 !bg-inherit">
                  Professional Design
                </summary>
                <div className="card-body !p-[0_0_0_1.1rem]">
                  <p>Fusce dapibus, tellus ac cursus commodo, tortor mauris condimentum nibh, ut fermentum massa justo sit amet risus. Cras mattis consectetur purus sit amet fermentum. Praesent commodo cursus magna, vel.</p>
                </div>
              </details>
              <details className="card plain">
                <summary className="accordion-button !text-[0.9rem] before:!text-[#fab758] hover:!text-[#fab758] cursor-pointer card-header !mb-0 !p-[0_0_.8rem_0] !border-0 !bg-inherit">
                  Top-Notch Support
                </summary>
                <div className="card-body !p-[0_0_0_1.1rem]">
                  <p>Fusce dapibus, tellus ac cursus commodo, tortor mauris condimentum nibh, ut fermentum massa justo sit amet risus. Cras mattis consectetur purus sit amet fermentum. Praesent commodo cursus magna, vel.</p>
                </div>
              </details>
              <details className="card plain">
                <summary className="accordion-button !text-[0.9rem] before:!text-[#fab758] hover:!text-[#fab758] cursor-pointer card-header !mb-0 !p-[0_0_.8rem_0] !border-0 !bg-inherit">
                  Header and Slider Options
                </summary>
                <div className="card-body !p-[0_0_0_1.1rem]">
                  <p>Fusce dapibus, tellus ac cursus commodo, tortor mauris condimentum nibh, ut fermentum massa justo sit amet risus. Cras mattis consectetur purus sit amet fermentum. Praesent commodo cursus magna, vel.</p>
                </div>
              </details>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}


