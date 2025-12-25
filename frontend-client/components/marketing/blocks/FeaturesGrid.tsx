interface FeatureItem {
  icon: string;
  title: string;
  description: string;
  link: string;
  linkText: string;
  color: string;
}

interface FeaturesGridProps {
  title: string;
  heading: string;
  items: FeatureItem[];
}

export function FeaturesGrid({ title, heading, items }: FeaturesGridProps) {
  const colorClasses: Record<string, string> = {
    yellow: '!text-[#fab758]',
    red: '!text-[#e2626b]',
    green: '!text-[#45c4a0]',
    blue: '!text-[#3f78e0]',
  };

  return (
    <section className="wrapper !bg-[#ffffff]">
      <div className="container pt-[4.5rem] xl:pt-24 lg:pt-24 md:pt-24">
        <div className="flex flex-wrap mx-[-15px] !text-center">
          <div className="md:w-10/12 xl:w-8/12 lg:w-8/12 w-full flex-[0_0_auto] !px-[15px] max-w-full xl:!ml-[16.66666667%] lg:!ml-[16.66666667%] md:!ml-[8.33333333%]">
            <h2 className="!text-[0.8rem] !tracking-[0.02rem] uppercase !text-[#aab0bc] !mb-3 !leading-[1.35]">{title}</h2>
            <h3 className="!text-[calc(1.315rem_+_0.78vw)] font-bold xl:!text-[1.9rem] !leading-[1.25] !mb-10 xl:!px-10">
              {heading}
            </h3>
          </div>
        </div>
        <div className="!relative">
          <div className="shape !rounded-[50%] !bg-[#edf2fc] rellax !w-[6rem] !h-[6rem] !absolute z-[1]" style={{ bottom: '-0.5rem', right: '-2.2rem', zIndex: 0 }}></div>
          <div className="shape bg-dot primary rellax !w-[6rem] !h-[7rem] absolute opacity-50 bg-[radial-gradient(#fab758_2px,transparent_2.5px)]" style={{ top: '-0.5rem', left: '-2.5rem', zIndex: 0 }}></div>
          <div className="flex flex-wrap mx-[-15px] xl:mx-[-12.5px] lg:mx-[-12.5px] md:mx-[-12.5px] !mt-[-25px] !text-center">
            {items.map((item, index) => (
              <div
                key={index}
                className="md:w-6/12 lg:w-6/12 xl:w-3/12 w-full flex-[0_0_auto] !px-[15px] max-w-full xl:!px-[12.5px] lg:!px-[12.5px] md:!px-[12.5px] !mt-[25px]"
              >
                <div className="card !shadow-[0_0.25rem_1.75rem_rgba(30,34,40,0.07)]">
                  <div className="card-body flex-[1_1_auto] p-[40px]">
                    <div className="text-4xl !mb-3 m-[0_auto]">{item.icon}</div>
                    <h4 className="!text-[1rem]">{item.title}</h4>
                    <p className="!mb-2">{item.description}</p>
                    <a href={item.link} className={`more hover ${colorClasses[item.color] || ''} focus:${colorClasses[item.color] || ''} hover:${colorClasses[item.color] || ''}`}>
                      {item.linkText}
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}


