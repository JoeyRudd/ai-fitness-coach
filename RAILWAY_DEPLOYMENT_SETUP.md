# Railway Deployment Setup Guide

## Overview
Your CI/CD pipeline now uses the official Railway CLI method for deployment instead of the deprecated `railway/deploy` action.

## What You Need to Set Up

### 1. Railway Project Setup
1. **Create a Railway account** at [railway.app](https://railway.app)
2. **Create a new project** for your AI Fitness Coach backend
3. **Connect your GitHub repository** to the Railway project

### 2. Get Your Railway Token
1. Go to your Railway project dashboard
2. Click on **Settings** → **Tokens** (or **Project Tokens**)
3. Click **Create Token**
4. **Copy the token** (you'll need this for GitHub secrets)
5. Give it a name like "GitHub Actions Deploy"

### 3. Add Railway Token to GitHub Secrets
1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `RAILWAY_TOKEN`
5. Value: Paste the token from Railway
6. Click **Add secret**

## How the Deployment Works

### Current Workflow:
```yaml
- name: Install Railway CLI
  run: npm install -g @railway/cli

- name: Deploy to Railway
  run: railway up --detach
  env:
    RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

### What Happens:
1. **Tests pass** → Deployment job starts
2. **Railway CLI installs** via npm
3. **railway up --detach** deploys your code
4. **--detach** flag means it won't wait for completion
5. **RAILWAY_TOKEN** authenticates the deployment

## Railway Project Configuration

### Automatic Detection:
Railway should automatically detect:
- ✅ **Python/FastAPI** application
- ✅ **Dockerfile** (you have one)
- ✅ **Port configuration** from your app

### Environment Variables:
Set these in Railway dashboard → Settings → Variables:
- `GEMINI_API_KEY` - Your Google AI API key
- `ALLOWED_ORIGINS` - Your frontend URL (Netlify domain)
- Any other environment variables your app needs

## Expected Results

### ✅ Successful Deployment:
- Backend deploys to Railway
- You get a Railway URL (e.g., `https://your-app.railway.app`)
- API is accessible at that URL

### ❌ Common Issues:
- **Missing RAILWAY_TOKEN** → Add the secret
- **Project not linked** → Make sure repository is connected to Railway project
- **Build failures** → Check Railway build logs

## Testing Your Deployment

### 1. Manual Test:
Visit your Railway URL + `/docs` (e.g., `https://your-app.railway.app/docs`)
Should see FastAPI documentation

### 2. API Test:
```bash
curl https://your-app.railway.app/api/v1/chat -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "history": []}'
```

## Next Steps

1. **Set up Railway project** and get token
2. **Add RAILWAY_TOKEN** to GitHub secrets
3. **Push to main branch** → Deployment should work
4. **Check Railway dashboard** for deployment status
5. **Test your deployed API**

## Troubleshooting

### If Railway CLI fails:
- Check Railway token is valid
- Verify repository is linked to Railway project
- Check Railway build logs for specific errors

### If deployment succeeds but app doesn't work:
- Check environment variables in Railway
- Verify port configuration
- Check Railway application logs

Your deployment should now work with the proper Railway CLI method! 🚀
