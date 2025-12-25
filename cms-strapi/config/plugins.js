module.exports = ({ env }) => {
  const plugins = {
    i18n: {
      enabled: true,
      config: {
        defaultLocale: 'fr',
        locales: ['fr', 'en', 'it'],
      },
    },
  };

  // Upload provider configuration
  const s3Bucket = env('STRAPI_S3_BUCKET');
  const s3AccessKeyId = env('STRAPI_S3_ACCESS_KEY_ID');
  const s3SecretAccessKey = env('STRAPI_S3_SECRET_ACCESS_KEY');
  const s3EndpointUrl = env('STRAPI_S3_ENDPOINT_URL');
  const s3PublicBaseUrl = env('STRAPI_S3_PUBLIC_BASE_URL');

  if (s3Bucket && s3AccessKeyId && s3SecretAccessKey) {
    // Use S3/R2 provider
    plugins.upload = {
      config: {
        provider: 'aws-s3',
        providerOptions: {
          accessKeyId: s3AccessKeyId,
          secretAccessKey: s3SecretAccessKey,
          region: env('STRAPI_S3_REGION', 'auto'),
          endpoint: s3EndpointUrl, // For R2: https://<account-id>.r2.cloudflarestorage.com
          params: {
            Bucket: s3Bucket,
          },
          baseUrl: s3PublicBaseUrl, // Optional CDN URL
          s3ForcePathStyle: true, // Required for R2
        },
        actionOptions: {
          upload: {},
          uploadStream: {},
          delete: {},
        },
        breakpoints: {
          xlarge: 1920,
          large: 1000,
          medium: 750,
          small: 500,
          xsmall: 64,
        },
      },
    };
  } else {
    // Use local provider (default)
    plugins.upload = {
      config: {
        breakpoints: {
          xlarge: 1920,
          large: 1000,
          medium: 750,
          small: 500,
          xsmall: 64,
        },
      },
    };
  }

  return plugins;
};
