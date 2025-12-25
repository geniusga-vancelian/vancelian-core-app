/**
 * Feature Grid Block - Renders a grid of features from Strapi CMS
 * Used in Dynamic Zone sections
 */

export interface FeatureItem {
  title: string;
  description?: string;
  icon?: string;
}

export interface FeatureGridBlockProps {
  title?: string;
  items?: FeatureItem[];
}

export function FeatureGridBlock({ title, items = [] }: FeatureGridBlockProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section className="py-16 md:py-24 bg-[#272727]">
      <div className="container mx-auto px-4">
        {title && (
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-12 text-gray-900">
            {title}
          </h2>
        )}
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {items.map((item, index) => (
            <div
              key={index}
              className="p-6 rounded-lg border border-gray-200 hover:shadow-lg transition-shadow"
            >
              {item.icon && (
                <div className="text-4xl mb-4 text-[#fab758]">
                  {item.icon}
                </div>
              )}
              
              <h3 className="text-xl font-semibold mb-3 text-gray-900">
                {item.title}
              </h3>
              
              {item.description && (
                <p className="text-gray-600">
                  {item.description}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}


