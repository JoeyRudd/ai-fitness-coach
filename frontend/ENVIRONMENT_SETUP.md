# Frontend Environment Setup

## Overview
The AI Fitness Coach frontend automatically detects whether it's running in development or production mode and uses the appropriate API endpoint.

## How It Works

### Development Mode
- Automatically detected when running `npm run dev`
- Uses Vite's proxy configuration to forward `/api/*` requests to your local backend
- API calls go to: `/api/v1/chat` (proxied to `http://localhost:8000/api/v1/chat`)

### Production Mode
- Automatically detected when deployed
- Uses the Railway backend URL directly: `https://outstanding-caring-production.up.railway.app/api/v1/chat`
- No environment variables needed

## Development Setup

### Local Development
1. **Start your backend** (FastAPI server on port 8000)

2. **Start your frontend**:
   ```bash
   npm run dev
   ```

### How It Works in Development
- Vite's proxy configuration automatically forwards `/api/*` requests to your local backend
- Your components use the proxy path: `/api/v1/chat`
- No `.env` file or environment variables needed

## Production Setup

### Netlify Deployment
- **No environment variables needed!**
- The app automatically uses the Railway backend URL in production
- Simply deploy and it works

### How It Works in Production
- The app detects it's running in production mode
- Automatically uses: `https://outstanding-caring-production.up.railway.app/api/v1/chat`
- No configuration required

## Troubleshooting

### API Calls Failing in Development
**Check:**
1. Is your FastAPI backend running on port 8000?
2. Is the Vite dev server running?
3. Check browser console for proxy errors

### API Calls Failing in Production
**Check:**
1. Is your Railway backend running and accessible?
2. Check browser console for network errors
3. Verify the Railway URL is correct in the code

## Example URLs

### Development
- API calls go to: `/api/v1/chat` (proxied to `http://localhost:8000/api/v1/chat`)

### Production
- API calls go to: `https://outstanding-caring-production.up.railway.app/api/v1/chat`

## Benefits of This Approach

- **Simpler**: No environment variables to manage
- **More reliable**: No risk of misconfigured environment variables
- **Easier deployment**: Works out of the box on Netlify
- **Consistent**: Same behavior across all environments
- **Maintainable**: Single source of truth for API endpoints

