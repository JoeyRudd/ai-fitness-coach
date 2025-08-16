# GitHub Actions CI/CD Pipeline Guide

## Overview
This project uses GitHub Actions for continuous integration and deployment. The pipeline automatically tests, builds, and deploys your application when you push to specific branches.

## Workflows

### 1. Main CI/CD Pipeline (`.github/workflows/ci.yml`)
**Triggers:** Push to `main` branch, Pull requests to `main`
**Purpose:** Full testing, linting, and deployment

**Jobs:**
- **Backend Tests**: Runs Python tests, linting, and type checking
- **Frontend Tests**: Runs TypeScript checks and builds
- **Deploy Backend**: Deploys to Railway and Fly.io (only on main branch)
- **Deploy Frontend**: Deploys to Netlify (only on main branch)

### 2. Development Tests (`.github/workflows/dev-tests.yml`)
**Triggers:** Push to any branch except `main`, Pull requests
**Purpose:** Quick testing without deployment

**Jobs:**
- **Backend Tests**: Basic Python testing
- **Frontend Tests**: Type checking and build verification

## How It Works

### On Push to Main Branch:
1. ✅ Run all tests (backend + frontend)
2. ✅ Run linting and type checking
3. ✅ If all tests pass, deploy backend to Railway and Fly.io
4. ✅ If all tests pass, deploy frontend to Netlify

### On Pull Request:
1. ✅ Run all tests (backend + frontend)
2. ✅ Run linting and type checking
3. ❌ No deployment (safety first!)

### On Push to Other Branches:
1. ✅ Run basic tests only
2. ❌ No deployment

## Required Secrets

You need to add these secrets in your GitHub repository settings:

### Backend Deployment
- `RAILWAY_TOKEN`: Your Railway deployment token
- `FLY_API_TOKEN`: Your Fly.io API token

### Frontend Deployment
- `NETLIFY_AUTH_TOKEN`: Your Netlify authentication token
- `NETLIFY_SITE_ID`: Your Netlify site ID

## How to Add Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with its corresponding value

## Local Testing

Before pushing, test locally:

```bash
# Backend tests
make test

# Frontend build
cd frontend && npm run build

# Linting
make lint

# Type checking
cd frontend && npm run type-check
```

## Troubleshooting

### Common Issues:

1. **Tests failing locally but passing in CI**
   - Check your Python/Node.js versions match CI
   - Ensure all dependencies are installed

2. **Deployment failures**
   - Verify your secrets are correctly set
   - Check deployment service status (Railway, Fly.io, Netlify)

3. **Linting failures**
   - Run `make lint` locally to see issues
   - Use `ruff check .` for specific problems

### Getting Help:

1. Check the **Actions** tab in your GitHub repository
2. Click on failed workflow runs to see detailed logs
3. Look for specific error messages in the job logs

## Best Practices

1. **Always test locally** before pushing
2. **Use feature branches** for development
3. **Keep PRs small** and focused
4. **Review CI results** before merging
5. **Update dependencies** regularly (Dependabot helps!)

## Customization

### Adding New Tests:
1. Add test files in `backend/tests/` or `frontend/tests/`
2. Update the workflow if you need new dependencies
3. Ensure tests run with existing commands

### Adding New Deployment Targets:
1. Add new deployment steps in the workflow
2. Set up required secrets
3. Test deployment process

### Modifying Triggers:
Edit the `on:` section in workflow files to change when actions run.

## Performance Tips

- **Use caching** for dependencies (already configured)
- **Run jobs in parallel** when possible
- **Keep workflows focused** on specific tasks
- **Use matrix builds** for multiple Python/Node versions if needed
