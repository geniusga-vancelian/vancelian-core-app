# Vancelian Core - Dev Frontend

**⚠️ DEV-ONLY - NOT FOR PRODUCTION USE ⚠️**

This is a minimal development frontend for testing the Vancelian Core API end-to-end locally.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# From repository root
docker-compose -f docker-compose.dev.yml up -d

# Access frontend
open http://localhost:3000
```

### Manual Setup

```bash
# Install dependencies
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local
echo "NEXT_PUBLIC_ZAND_WEBHOOK_SECRET=dev-webhook-secret-for-testing" >> .env.local

# Start dev server
npm run dev
```

## Features

- JWT Token injection (sessionStorage)
- Wallet balance viewer
- Transaction history
- Investment creation
- Admin/Compliance actions (release/reject deposits)
- ZAND webhook simulator

## Documentation

See [../docs/local_frontend.md](../docs/local_frontend.md) for complete documentation including:
- E2E test flows
- Troubleshooting
- Environment variables
- Architecture notes


