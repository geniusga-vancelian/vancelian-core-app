# Strapi CMS Runbook

## Overview

Strapi is used as the CMS (Content Management System) for:
1. **Site vitrine** (marketing pages, SEO, multi-language)
2. **Offer marketing** (layout, media, timeline, documents)
3. **Trusted Partners** (partner profiles)
4. **Blog/News/Articles**

FastAPI remains the business engine (investments, wallets, ledger, transactions).

## Architecture

- **CMS Database**: `vancelian_cms` (separate from `vancelian_core`)
- **Port**: `1337` (admin panel: http://localhost:1337/admin)
- **API**: http://localhost:1337/api
- **Multi-language**: i18n plugin enabled (fr/en/it, default: fr)
- **Storage**: Cloudflare R2 (S3-compatible) or local fallback

## Setup

### 1. Environment Variables

Add to `.env.dev` (see `.env.dev.example`):

```bash
# Strapi Frontend
NEXT_PUBLIC_STRAPI_URL=http://localhost:1337
STRAPI_URL=http://localhost:1337

# Strapi Database
STRAPI_DATABASE_URL=postgresql://vancelian:vancelian_password@postgres:5432/vancelian_cms
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=vancelian_cms
DATABASE_USERNAME=vancelian
DATABASE_PASSWORD=vancelian_password
DATABASE_SSL=false

# Strapi Secrets (generate with: openssl rand -base64 32)
STRAPI_APP_KEYS=key1,key2,key3,key4
STRAPI_API_TOKEN_SALT=salt1
STRAPI_ADMIN_JWT_SECRET=secret1
STRAPI_JWT_SECRET=secret2
STRAPI_TRANSFER_TOKEN_SALT=salt2

# Strapi Storage (optional, falls back to local if not set)
STRAPI_S3_PROVIDER=aws-s3
STRAPI_S3_ACCESS_KEY_ID=your-key-id
STRAPI_S3_SECRET_ACCESS_KEY=your-secret-key
STRAPI_S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
STRAPI_S3_REGION=auto
STRAPI_S3_BUCKET=your-strapi-media-bucket
STRAPI_S3_PUBLIC_BASE_URL=https://your-cdn-domain.com
```

### 2. Database Setup

The database is automatically created when the postgres service starts. Verify:

```bash
docker compose -f docker-compose.dev.yml exec postgres psql -U vancelian -d vancelian_cms -c "\dt"
```

### 3. Start Strapi

```bash
docker compose -f docker-compose.dev.yml up -d cms-strapi
```

Wait for Strapi to initialize, then access:
- **Admin**: http://localhost:1337/admin
- **API**: http://localhost:1337/api

On first run, you'll need to create an admin user through the web interface.

## Content Types

The following content types must be created in Strapi Admin:

### A) Site Vitrine

#### 1. Global (Single Type)
- `brand_name` (Text, short text)
- `logo` (Media, single image)
- `header_navigation` (Component, repeatable)
  - `label` (Text)
  - `url` (Text)
  - `is_external` (Boolean)
- `footer_links` (Component, repeatable)
  - `label` (Text)
  - `url` (Text)
- `socials` (Component, repeatable)
  - `platform` (Text)
  - `url` (Text)
- `legal_links` (Component, repeatable)
  - `label` (Text)
  - `url` (Text)

**Enable i18n**: Yes

#### 2. Page (Collection Type)
- `slug` (UID, unique, required)
- `title` (Text, required)
- `seo` (Component, single)
  - `metaTitle` (Text)
  - `metaDescription` (Text)
  - `ogImage` (Media, single image)
- `sections` (Dynamic Zone)
  - Hero component:
    - `title` (Text)
    - `subtitle` (Text)
    - `ctaLabel` (Text)
    - `ctaUrl` (Text)
    - `media` (Media, single)
  - Features component:
    - `items` (JSON, array of objects)
  - Testimonials component:
    - `items` (JSON, array of objects)
  - FAQ component:
    - `items` (JSON, array of {question, answer})
  - CTA component:
    - `title` (Text)
    - `text` (Text)
    - `buttonLabel` (Text)
    - `buttonUrl` (Text)
  - MediaGallery component:
    - `images` (Media, multiple)
  - RichText component:
    - `content` (Rich text or Textarea for markdown)

**Enable i18n**: Yes

### B) Offers Marketing

#### 3. OfferMarketing (Collection Type)
- `offer_id` (Text, required, unique) - UUID string from FastAPI
- `title` (Text, required)
- `subtitle` (Text)
- `location` (Text)
- `highlights` (JSON, array of strings)
- `why_invest` (JSON, array of {title, text}, max 6 items)
- `metrics` (JSON, object)
- `cover_media` (Media, single image)
- `promo_video` (Media, single video)
- `gallery` (Media, multiple images)
- `documents` (Media, multiple)
- `seo` (Component, single)
  - `metaTitle` (Text)
  - `metaDescription` (Text)
  - `ogImage` (Media, single image)

**Enable i18n**: Yes

#### 4. OfferUpdate (Collection Type)
- `offer_id` (Text, required) - UUID string from FastAPI
- `date` (Date, required)
- `title` (Text, required, max 80 chars)
- `description` (Text, max 240 chars)
- `link_url` (Text, optional)
- `linked_article` (Relation, Article, optional)
- `media` (Media, multiple)
- `is_key_milestone` (Boolean, default: false)

**Enable i18n**: Yes

### C) Partners

#### 5. Partner (Collection Type)
- `slug` (UID, unique, required)
- `name` (Text, required)
- `legal_name` (Text)
- `website` (Text)
- `address` (Text)
- `description_markdown` (Textarea)
- `ceo_name` (Text)
- `ceo_quote` (Text)
- `ceo_photo` (Media, single image)
- `documents` (Media, multiple)
- `videos` (Media, multiple)
- `gallery` (Media, multiple)
- `seo` (Component, single)
  - `metaTitle` (Text)
  - `metaDescription` (Text)
  - `ogImage` (Media, single image)

**Enable i18n**: Yes

#### 6. PartnerProject (Collection Type)
- `partner` (Relation, Partner, required)
- `title` (Text, required)
- `description` (Textarea)
- `year` (Number)
- `location` (Text)
- `cover` (Media, single image)
- `gallery` (Media, multiple)
- `link_url` (Text)

**Enable i18n**: Yes

### D) Blog/News

#### 7. Article (Collection Type)
- `slug` (UID, unique, required)
- `title` (Text, required)
- `excerpt` (Text)
- `content_markdown` (Textarea or Rich text)
- `cover_image` (Media, single image)
- `gallery` (Media, multiple)
- `promo_video` (Media, single video)
- `published_at` (DateTime)
- `is_featured` (Boolean, default: false)
- `offer_id` (Text, optional) - UUID string from FastAPI (for offer-specific news)
- `seo` (Component, single)
  - `metaTitle` (Text)
  - `metaDescription` (Text)
  - `ogImage` (Media, single image)

**Enable i18n**: Yes

**Optional**: Category, Tag (if needed for filtering)

## API Permissions

Configure in Strapi Admin → Settings → Users & Permissions Plugin → Roles → Public:

### Allow Public Read Access

- `global` → `find` (GET)
- `pages` → `find`, `findOne` (GET)
- `offer-marketings` → `find`, `findOne` (GET)
- `offer-updates` → `find`, `findOne` (GET)
- `articles` → `find`, `findOne` (GET)
- `partners` → `find`, `findOne` (GET)
- `partner-projects` → `find`, `findOne` (GET)

**Note**: Write access is restricted to authenticated admin users only.

## Frontend Integration

### Client Library

Use `frontend-client/lib/cms.ts`:

```typescript
import { getGlobal, getPage, getOfferMarketing, getOfferUpdates, getArticles, getPartner } from '@/lib/cms';

// Get global content
const global = await getGlobal('fr');

// Get page
const page = await getPage('about', 'fr');

// Get offer marketing
const offerMarketing = await getOfferMarketing('offer-uuid-here', 'fr');

// Get offer updates
const updates = await getOfferUpdates('offer-uuid-here', 'fr', 10);

// Get articles
const articles = await getArticles({ locale: 'fr', featured: true });

// Get partner
const partner = await getPartner('partner-slug', 'fr');
```

### Configuration

All URLs use `getStrapiApiUrl()` from `lib/config.ts` (no hardcoding):
- Development: `http://localhost:1337`
- Production: `NEXT_PUBLIC_STRAPI_URL` env var

## API Endpoints Examples

### Get Global Content
```
GET /api/global?locale=fr&populate=*
```

### Get Page by Slug
```
GET /api/pages?filters[slug][$eq]=about&locale=fr&populate=*
```

### Get Offer Marketing
```
GET /api/offer-marketings?filters[offer_id][$eq]=123e4567-e89b-12d3-a456-426614174000&locale=fr&populate=*
```

### Get Offer Updates
```
GET /api/offer-updates?filters[offer_id][$eq]=123e4567-e89b-12d3-a456-426614174000&locale=fr&sort=date:desc&populate=*
```

### Get Articles
```
GET /api/articles?filters[published_at][$notNull]=true&locale=fr&sort=published_at:desc&populate=*
GET /api/articles?filters[offer_id][$eq]=123e4567-e89b-12d3-a456-426614174000&locale=fr&populate=*
GET /api/articles?filters[is_featured][$eq]=true&locale=fr&populate=*
```

### Get Partners
```
GET /api/partners?locale=fr&sort=name:asc&populate=*
GET /api/partners?filters[slug][$eq]=partner-slug&locale=fr&populate=*
```

## Storage

### Local Storage (Default)
If `STRAPI_S3_PROVIDER` is not set or `local`, media is stored in:
- Container: `/app/public/uploads/`
- Volume: `cms_strapi_uploads`

### R2/S3 Storage
Configure via environment variables (see Setup section). Media will be stored in the configured bucket.

## Multi-Language (i18n)

- **Default locale**: `fr`
- **Available locales**: `fr`, `en`, `it`
- All content types support i18n
- Use `?locale=fr` (or `en`, `it`) in API requests

## Linking to FastAPI Offers

Content in Strapi links to FastAPI offers via `offer_id` (UUID string):
- No foreign key constraint (loose coupling)
- FastAPI remains source of truth for business data
- Strapi handles marketing/content presentation only

## Development Workflow

1. **Start services**: `docker compose -f docker-compose.dev.yml up -d`
2. **Access Strapi Admin**: http://localhost:1337/admin
3. **Create/Edit content** in Strapi Admin
4. **Frontend reads** via `lib/cms.ts` functions
5. **FastAPI handles** business logic (investments, transactions)

## Troubleshooting

### Strapi won't start
- Check database is running: `docker compose -f docker-compose.dev.yml ps postgres`
- Verify database exists: `docker compose -f docker-compose.dev.yml exec postgres psql -U vancelian -l`
- Check logs: `docker compose -f docker-compose.dev.yml logs cms-strapi`

### 401/403 errors on API
- Verify Public role permissions in Strapi Admin
- Check API endpoint is correct (use `/api/` prefix)

### Images not loading
- Check storage configuration (local vs S3/R2)
- Verify media files exist in Strapi Admin → Media Library
- Check CDN URL if using `STRAPI_S3_PUBLIC_BASE_URL`

### i18n not working
- Verify i18n plugin is enabled in `config/plugins.js`
- Check locale is included in available locales
- Ensure content type has i18n enabled

## Production Considerations

1. **Generate secure secrets** using `openssl rand -base64 32`
2. **Configure R2/S3 storage** for media
3. **Set up CDN** for media delivery (`STRAPI_S3_PUBLIC_BASE_URL`)
4. **Enable SSL** for database connection if required
5. **Review API permissions** before going live
6. **Backup database** regularly (`vancelian_cms`)

---

## Validation Checklist

### 1. Strapi Service
- [ ] Strapi is running: `docker compose -f docker-compose.dev.yml ps cms-strapi`
- [ ] Admin accessible: http://localhost:1337/admin
- [ ] API accessible: http://localhost:1337/api

### 2. Content Types Created
- [ ] Global (single type) created with i18n enabled
- [ ] Page (collection) created with i18n enabled
- [ ] OfferMarketing created with i18n enabled
- [ ] OfferUpdate created with i18n enabled
- [ ] Partner created with i18n enabled
- [ ] PartnerProject created with i18n enabled
- [ ] Article created with i18n enabled

### 3. Permissions API
- [ ] Public role permissions configured (find/findOne only)
- [ ] No create/update/delete on Public role
- [ ] Test API endpoints return 200 OK

### 4. API Endpoints Test
```bash
# Global
curl http://localhost:1337/api/global?locale=fr

# Pages
curl "http://localhost:1337/api/pages?filters[slug][\$eq]=home&locale=fr&populate=*"

# Offer Marketing (replace with actual offer_id UUID)
curl "http://localhost:1337/api/offer-marketings?filters[offer_id][\$eq]=<uuid>&locale=fr&populate=*"

# Offer Updates
curl "http://localhost:1337/api/offer-updates?filters[offer_id][\$eq]=<uuid>&locale=fr&sort=date:desc&populate=*"

# Articles
curl "http://localhost:1337/api/articles?filters[status][\$eq]=PUBLISHED&locale=fr&populate=*"

# Partners
curl "http://localhost:1337/api/partners?locale=fr&populate=*"
```

All should return `200 OK` with JSON data (even if empty arrays).

### 5. Frontend Integration
- [ ] Offer page loads: http://localhost:3000/offers/<id>
- [ ] Marketing content displays (if exists in Strapi)
- [ ] Timeline displays OfferUpdates (if exists in Strapi)
- [ ] Articles display (if exists in Strapi)
- [ ] Fallback to FastAPI works when Strapi content missing
- [ ] No hardcoded URLs in console
- [ ] Media URLs resolve correctly (local or CDN)

### 6. Environment Variables
- [ ] `.env.dev` contains `NEXT_PUBLIC_STRAPI_URL=http://localhost:1337`
- [ ] Frontend services have `NEXT_PUBLIC_STRAPI_URL` in docker-compose
- [ ] Strapi secrets generated (not default values)

### 7. Audits
```bash
make audit-runtime
make audit-db
# Should pass (WARN acceptable)
```

