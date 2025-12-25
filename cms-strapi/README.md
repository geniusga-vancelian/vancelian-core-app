# Vancelian CMS - Strapi

This is the Strapi CMS instance for Vancelian, managing content for:
- Marketing pages (site vitrine)
- Offer marketing materials
- Trusted Partners profiles
- Blog/News/Articles

## Quick Start

1. **Start the service**:
   ```bash
   docker compose -f ../docker-compose.dev.yml up -d cms-strapi
   ```

2. **Access admin panel**: http://localhost:1337/admin

3. **Create admin user** on first run through the web interface

4. **Configure content types** as documented in `../docs/CMS_STRAPI_RUNBOOK.md`

## Development

- **API**: http://localhost:1337/api
- **Admin**: http://localhost:1337/admin
- **Database**: `vancelian_cms` (separate from `vancelian_core`)

## Configuration

See `../docs/CMS_STRAPI_RUNBOOK.md` for:
- Environment variables
- Content types setup
- API permissions
- Storage configuration (R2/S3)
- Multi-language setup (i18n)

## Notes

- Content types are created via Strapi Admin UI (see runbook)
- FastAPI handles business logic; Strapi handles marketing/content
- Linking via `offer_id` (UUID string) - loose coupling

