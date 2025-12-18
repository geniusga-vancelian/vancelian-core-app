# Frontend Client Setup & Verification

## Quick Start

1. **Start the stack:**
   ```bash
   cd /Users/gael/Documents/Cursor/vancelian-core-app
   docker compose -f docker-compose.dev.yml up -d
   ```

2. **Verify backend is running:**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"ok"}`

3. **Open the frontend:**
   - Navigate to: http://localhost:3000
   - You should see the login page

## How to Verify Dashboard

### Step 1: Login
1. Open http://localhost:3000/login
2. Use credentials:
   - Email: `gaelitier@gmail.com`
   - Password: `test123456`
3. After successful login, you should be redirected to `/` (dashboard)

### Step 2: Verify Dashboard Loads
The dashboard should display:
- **Wallet Cards** (4 cards):
  - Total Balance (AED)
  - Available Balance (green)
  - Under Review (yellow) - blocked balance
  - Invested (blue) - locked balance
- **Latest Transactions Table**:
  - Type (DEPOSIT/WITHDRAWAL/INVESTMENT)
  - Status
  - Amount
  - Date

### Step 3: Check Network Requests (DevTools)
1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Refresh the dashboard page
4. Verify these requests return **200 OK**:
   - `GET /api/v1/wallet?currency=AED`
   - `GET /api/v1/transactions?limit=20`
   - `GET /api/v1/me` (if called)

### Step 4: Handle Errors
If you see an error panel:
- **Check the trace_id** in the error message
- **Check the status code**:
  - `401` or `403`: Token expired/invalid → redirects to login
  - `404`: Account not found → shows DEV bootstrap button (if on localhost)
  - `500`: Backend error → check backend logs

### Step 5: DEV Bootstrap (if needed)
If you see "Missing AED Accounts" message:
- Click "Create AED Accounts (DEV)" button
- This calls `POST /dev/v1/bootstrap/user`
- Dashboard will reload automatically

## Troubleshooting

### Dashboard shows "Loading..." forever
- Check browser console for errors
- Verify backend is running: `curl http://localhost:8000/health`
- Check network tab for failed requests

### 401/403 Errors
- Token may be expired or invalid
- Clear sessionStorage: `sessionStorage.clear()` in console
- Re-login

### Missing Accounts Error
- User exists but has no wallet accounts
- Use DEV bootstrap button (localhost only)
- Or register a new user (creates accounts automatically)

### API Base URL Issues
- Check console for `[api] baseUrl=` log
- Should be: `http://localhost:8000`
- If different, check `NEXT_PUBLIC_API_BASE_URL` in docker-compose.dev.yml

## API Endpoints Used

- `GET /api/v1/wallet?currency=AED` - Wallet balances
- `GET /api/v1/transactions?limit=20` - Latest transactions
- `GET /api/v1/me` - User profile (optional)
- `POST /dev/v1/bootstrap/user` - Create accounts (DEV only)

## Environment Variables

- `NEXT_PUBLIC_API_BASE_URL`: API base URL (default: `http://localhost:8000`)
- Set in `docker-compose.dev.yml` under `frontend-client` service

