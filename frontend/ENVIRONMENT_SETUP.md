# Frontend Environment Setup

## Overview
The AI Fitness Coach frontend needs to know where your backend API is located. This is configured through the `VITE_API_BASE` environment variable.

## Environment Variables

### Required Variables
- `VITE_API_BASE` - The base URL of your backend API

## Development Setup

### Local Development
1. **Create a `.env` file** in the `frontend/` directory:
   ```bash
   VITE_API_BASE=http://localhost:8000
   ```

2. **Start your backend** (FastAPI server on port 8000)

3. **Start your frontend**:
   ```bash
   npm run dev
   ```

### How It Works in Development
- The `.env` file sets `VITE_API_BASE=http://localhost:8000`
- Vite's proxy configuration forwards `/api/*` requests to your local backend
- Your components use the full URL: `http://localhost:8000/api/v1/chat`

## Production Setup

### Netlify Deployment
1. **Go to your Netlify dashboard** → Your site → **Site settings** → **Environment variables**
2. **Add a new variable:**
   - Key: `VITE_API_BASE`
   - Value: `https://your-railway-app.railway.app` (your actual Railway backend URL)

### Alternative: Build-time Configuration
You can also set this in your `netlify.toml`:
```toml
[build.environment]
  VITE_API_BASE = "https://your-railway-app.railway.app"
```

**⚠️ Important:** Replace `your-railway-app.railway.app` with your actual Railway backend URL!

## Environment Configuration File

The app now uses a centralized environment configuration (`src/config/environment.ts`) that:

- Automatically detects development vs production
- Provides fallbacks for missing environment variables
- Includes helper functions for building API URLs
- Logs configuration details in development

## Troubleshooting

### Error: "VITE_API_BASE environment variable is not set!"
**Solution:** Set the `VITE_API_BASE` environment variable in your deployment platform.

### API Calls Failing in Production
**Check:**
1. Is `VITE_API_BASE` set correctly in your deployment environment?
2. Does the URL point to your actual Railway backend?
3. Is your Railway backend running and accessible?

### Development Proxy Not Working
**Check:**
1. Is your FastAPI backend running on port 8000?
2. Does your `.env` file contain `VITE_API_BASE=http://localhost:8000`?
3. Restart your frontend dev server after changing `.env`

## Example URLs

### Development
- `VITE_API_BASE=http://localhost:8000`
- API calls go to: `http://localhost:8000/api/v1/chat`

### Production
- `VITE_API_BASE=https://my-fitness-app.railway.app`
- API calls go to: `https://my-fitness-app.railway.app/api/v1/chat`

## Security Notes

- Environment variables prefixed with `VITE_` are exposed to the browser
- This is safe for API base URLs as they're not sensitive secrets
- Never put API keys or passwords in `VITE_` prefixed variables

