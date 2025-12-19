# S3/R2 Storage Setup for Offers Media & Documents

This document describes how to configure Cloudflare R2 (or AWS S3) for storing offer media files (images/videos) and documents (PDFs, etc.).

## Overview

The system uses **presigned URLs** for direct upload/download, meaning:
- Files are uploaded **directly** from the frontend to S3/R2 (not proxied through backend)
- Files are downloaded **directly** from S3/R2 (not proxied through backend)
- Backend only stores **metadata** in PostgreSQL
- Backend generates presigned URLs for upload/download operations

## Cloudflare R2 Setup

### 1. Create R2 Bucket

1. Log in to Cloudflare Dashboard
2. Go to **R2** → **Create bucket**
3. Choose a bucket name (e.g., `vancelian-offers`)
4. Select a location (e.g., `WNAM` for Western North America)

### 2. Create API Token

1. Go to **R2** → **Manage R2 API Tokens**
2. Click **Create API Token**
3. Set permissions:
   - **Object Read & Write** (for presigned URLs)
   - **Bucket** scope: Select your bucket
4. Copy:
   - **Access Key ID**
   - **Secret Access Key**

### 3. Get R2 Endpoint URL

R2 endpoint format:
```
https://<account-id>.r2.cloudflarestorage.com
```

To find your account ID:
- Go to Cloudflare Dashboard → Right sidebar → **Account ID**

Example:
```
https://abc123def456.r2.cloudflarestorage.com
```

### 4. Configure CORS

R2 buckets require CORS configuration to allow direct uploads from frontend.

1. Go to your R2 bucket → **Settings** → **CORS Policy**
2. Add the following CORS configuration:

```json
[
  {
    "AllowedOrigins": [
      "http://localhost:3000",
      "http://localhost:3001",
      "http://127.0.0.1:3000",
      "http://127.0.0.1:3001"
    ],
    "AllowedMethods": ["GET", "PUT", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

**For production**, replace `localhost` origins with your actual frontend domains.

### 5. Environment Variables

Add to `.env.dev` (or your environment file):

```bash
# S3/R2 Storage Configuration
STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
S3_REGION=auto
S3_ACCESS_KEY_ID=<your-access-key-id>
S3_SECRET_ACCESS_KEY=<your-secret-access-key>
S3_BUCKET=vancelian-offers
S3_PUBLIC_BASE_URL=  # Optional: CDN URL if using Cloudflare CDN
S3_PRESIGN_EXPIRES_SECONDS=900
S3_KEY_PREFIX=offers

# Upload size limits (in bytes)
S3_MAX_DOCUMENT_SIZE=52428800  # 50MB
S3_MAX_VIDEO_SIZE=209715200    # 200MB
S3_MAX_IMAGE_SIZE=10485760      # 10MB
```

## AWS S3 Setup (Alternative)

If using AWS S3 instead of R2:

```bash
STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=  # Leave empty for AWS
S3_REGION=eu-west-1  # Your AWS region
S3_ACCESS_KEY_ID=<aws-access-key>
S3_SECRET_ACCESS_KEY=<aws-secret-key>
S3_BUCKET=your-bucket-name
S3_PUBLIC_BASE_URL=https://your-bucket.s3.eu-west-1.amazonaws.com  # Optional
S3_PRESIGN_EXPIRES_SECONDS=900
S3_KEY_PREFIX=offers
```

### AWS S3 CORS Configuration

Add CORS policy to your S3 bucket:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "HEAD"],
    "AllowedOrigins": [
      "http://localhost:3000",
      "http://localhost:3001",
      "http://127.0.0.1:3000",
      "http://127.0.0.1:3001"
    ],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

## Object Key Structure

All objects are stored with the following key pattern:
```
{S3_KEY_PREFIX}/{offer_id}/{upload_type}/{file_name}
```

Example:
```
offers/89aa24ec-d02d-45d4-aa7e-14540c13db0a/media/cover-image.jpg
offers/89aa24ec-d02d-45d4-aa7e-14540c13db0a/documents/brochure.pdf
```

## URL Resolution

The system resolves URLs in the following order:

1. **If `url` field is set in database** → Return that URL (CDN/public URL)
2. **If `S3_PUBLIC_BASE_URL` is configured** → Return `{S3_PUBLIC_BASE_URL}/{key}`
3. **Otherwise** → Return `null` and use presigned download endpoint

## Presigned URLs

- **Upload (PUT)**: Valid for 15 minutes (900 seconds) by default
- **Download (GET)**: Valid for 15 minutes (900 seconds) by default
- Expiration time is configurable via `S3_PRESIGN_EXPIRES_SECONDS`

## File Size Limits

Default limits (configurable):
- **Documents**: 50MB
- **Videos**: 200MB
- **Images**: 10MB

## MIME Type Validation

### Media (Images/Videos)
- **Images**: Must start with `image/` (e.g., `image/jpeg`, `image/png`)
- **Videos**: Must start with `video/` (e.g., `video/mp4`, `video/webm`)

### Documents
Allowed MIME types:
- `application/pdf`
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (.xlsx)
- `application/vnd.ms-excel` (.xls)
- `application/msword` (.doc)
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (.docx)

## Testing

### 1. Test Presigned Upload URL

```bash
# Get presigned URL
curl -X POST "http://localhost:8000/admin/v1/offers/{offer_id}/uploads/presign" \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "upload_type": "media",
    "file_name": "test.jpg",
    "mime_type": "image/jpeg",
    "size_bytes": 1024000,
    "media_type": "IMAGE"
  }'

# Response:
# {
#   "upload_url": "https://...",
#   "key": "offers/{offer_id}/media/test.jpg",
#   "required_headers": {"Content-Type": "image/jpeg"},
#   "expires_in": 900
# }

# Upload file directly to S3/R2
curl -X PUT "<upload_url>" \
  -H "Content-Type: image/jpeg" \
  --data-binary @test.jpg
```

### 2. Create Media Metadata

```bash
curl -X POST "http://localhost:8000/admin/v1/offers/{offer_id}/media" \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "offers/{offer_id}/media/test.jpg",
    "mime_type": "image/jpeg",
    "size_bytes": 1024000,
    "type": "IMAGE",
    "sort_order": 0,
    "is_cover": true,
    "visibility": "PUBLIC",
    "width": 1920,
    "height": 1080
  }'
```

### 3. List Media

```bash
curl "http://localhost:8000/admin/v1/offers/{offer_id}/media" \
  -H "Authorization: Bearer <ADMIN_JWT>"
```

### 4. Get Presigned Download URL (Public)

```bash
curl "http://localhost:8000/api/v1/offers/{offer_id}/media/{media_id}/download" \
  -H "Authorization: Bearer <USER_JWT>"
```

## Troubleshooting

### CORS Errors

If you see CORS errors in browser console:
1. Verify CORS policy is correctly configured in R2/S3
2. Check that frontend origin matches `AllowedOrigins` in CORS policy
3. Ensure `AllowedMethods` includes `PUT` for uploads

### Presigned URL Expired

- Presigned URLs expire after `S3_PRESIGN_EXPIRES_SECONDS` (default: 900 seconds)
- Frontend should upload immediately after receiving presigned URL
- If upload fails, request a new presigned URL

### File Not Found

- Verify object key matches exactly (case-sensitive)
- Check that file was successfully uploaded to S3/R2
- Verify bucket name and region are correct

### Access Denied

- Verify `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY` are correct
- Check API token permissions in Cloudflare (or IAM policy in AWS)
- Ensure bucket exists and is accessible

## Security Notes

1. **Never commit credentials** to version control
2. **Use environment variables** for all S3/R2 credentials
3. **Rotate API tokens** regularly
4. **Limit API token permissions** to minimum required (Object Read & Write)
5. **Use CDN** (`S3_PUBLIC_BASE_URL`) for public assets to reduce presigned URL usage
6. **Validate file types and sizes** on both frontend and backend

