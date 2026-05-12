# Deployment Guide: Food Price Anomaly Detection System

## Quick Start - Heroku Deployment

### Prerequisites
- Heroku CLI installed ([install here](https://devcenter.heroku.com/articles/heroku-cli))
- Git installed
- GitHub account

### Step 1: Create Heroku App

```bash
heroku login
heroku create your-app-name
heroku stack:set heroku-22  # Use newer stack for Python 3.11
```

### Step 2: Configure Environment

```bash
# Copy environment file
cp .env.example .env

# Set Heroku environment variables
heroku config:set LOG_LEVEL=INFO
heroku config:set PYTHONUNBUFFERED=1
```

### Step 3: Deploy to Heroku

```bash
# Via Git (recommended)
git remote add heroku https://git.heroku.com/your-app-name.git
git push heroku main

# OR via GitHub integration
# 1. Go to https://dashboard.heroku.com/apps/your-app-name/deploy/github
# 2. Search for this repository and connect
# 3. Enable automatic deploys
```

### Step 4: Monitor Deployment

```bash
# View logs
heroku logs --tail

# Check app status
heroku ps

# View app URL
heroku open
```

## Docker Local Deployment

### Run with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Access:
# - Streamlit UI: http://localhost:8501
# - FastAPI: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Build Docker Image Manually

```bash
# Streamlit app
docker build -t food-price-anomaly:latest -f Dockerfile .
docker run -p 8501:8501 food-price-anomaly:latest

# FastAPI backend
docker build -t food-price-api:latest -f Dockerfile.api .
docker run -p 8000:8000 food-price-api:latest
```

## Production Configuration

### Heroku Resource Types

**Dyno Types:**
- `web`: Handles HTTP requests (Streamlit UI)
- `api`: Handles API requests (FastAPI backend)

**Recommended Setup:**
```bash
# Scale dynos (Standard-2x minimum recommended)
heroku dyno:type Standard-2x -a your-app-name
heroku ps:scale web=1 api=1
```

### Performance Tuning

**For Streamlit (UI):**
```bash
# Increase memory for large datasets
heroku ps:type Standard-2x

# Enable client error details in production
export STREAMLIT_CLIENT_SHOW_ERROR_DETAILS=false
```

**For FastAPI (API):**
```bash
# Set optimal worker count (4 per CPU core)
heroku config:set API_WORKERS=4

# Enable request logging
heroku config:set LOG_LEVEL=DEBUG
```

## Monitoring & Maintenance

### View Real-time Metrics

```bash
# CPU and Memory usage
heroku ps -a your-app-name

# View all config variables
heroku config -a your-app-name

# Check Dyno uptime
heroku run bash -a your-app-name
ps aux | grep streamlit
```

### Update Requirements

```bash
# When dependencies change:
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push heroku main
```

### Database/Storage (if needed)

```bash
# Add Heroku Postgres
heroku addons:create heroku-postgresql:hobby-dev -a your-app-name

# View connection string
heroku config:get DATABASE_URL
```

## Troubleshooting

### App Won't Start

```bash
# Check logs
heroku logs --tail -a your-app-name

# Common issues:
# 1. Missing requirements - ensure requirements.txt is committed
# 2. Port binding - app must listen on $PORT environment variable
# 3. Memory issues - check with: heroku ps
```

### Slow Performance

```bash
# Increase dyno size
heroku ps:type Performance-M

# Monitor performance
heroku metrics -a your-app-name
```

### Deploy Failed

```bash
# Review build logs
heroku builds -a your-app-name

# Rebuild if needed
git push heroku main --force-with-lease
```

## API Endpoints (Production URLs)

```
Base URL: https://your-app-name.herokuapp.com

UI: https://your-app-name.herokuapp.com/
API Health: https://your-app-name.herokuapp.com/api/health
API Docs: https://your-app-name.herokuapp.com/api/docs
```

## Cleanup & Destruction

```bash
# Stop app without deleting
heroku ps:scale web=0

# Delete app completely
heroku apps:destroy --app your-app-name
```

## Additional Resources

- [Heroku Python Support](https://devcenter.heroku.com/articles/python-support)
- [Streamlit on Heroku](https://docs.streamlit.io/knowledge-base/tutorials/deploy/deploy-streamlit-heroku)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/concepts/)
- [Docker on Heroku](https://devcenter.heroku.com/articles/container-registry-and-runtime)
