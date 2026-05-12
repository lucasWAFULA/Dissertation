# Google Cloud Run Deployment Guide

## Food Price Anomaly Detection System on Google Cloud

This guide walks through deploying the Streamlit + FastAPI application to Google Cloud Run, a fully managed serverless platform.

---

## 🎯 Why Google Cloud Run?

✅ **Advantages over Heroku:**
- Free tier: 2 million requests/month + 360,000 GB-seconds
- Pay-per-use (no monthly minimum)
- No credit card required initially
- Auto-scaling from 0 to 100+ instances
- Native Docker container support
- Integrates with Google Cloud ecosystem

---

## 📋 Prerequisites

1. **Google Cloud Account** - Sign up at [https://cloud.google.com](https://cloud.google.com)
2. **Google Cloud SDK** - Install from [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
3. **Docker** - For local testing
4. **Git** - Already have this!

---

## 🚀 Quick Deployment (5 Minutes)

### Step 1: Initialize Google Cloud

```bash
# Install/update Google Cloud SDK
gcloud components update

# Login to Google Cloud
gcloud auth login

# Set your project (replace YOUR_PROJECT_ID with your Google Cloud Project ID)
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### Step 2: Deploy to Cloud Run

**Option A: Simple One-Command Deploy**

```bash
# From project root directory
gcloud run deploy food-price-anomaly \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10
```

**Option B: Using Cloud Build (CI/CD)**

```bash
# Submit build to Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Then deploy
gcloud run deploy food-price-anomaly \
  --image gcr.io/YOUR_PROJECT_ID/food-price-app:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2
```

### Step 3: Get Your Application URL

```bash
# View deployment status
gcloud run services describe food-price-anomaly --region us-central1

# Get the service URL
gcloud run services describe food-price-anomaly \
  --region us-central1 \
  --format 'value(status.url)'
```

**Your app will be available at:**
```
https://food-price-anomaly-xxxxx-uc.a.run.app
```

---

## 🔧 Configuration Details

### Cloud Run Service Settings

| Setting | Value | Why |
|---------|-------|-----|
| **Memory** | 2Gi | Enough for Streamlit + model |
| **CPU** | 2 | Handles concurrent requests |
| **Timeout** | 300s | For large file uploads |
| **Max Instances** | 10 | Prevents runaway costs |
| **Min Instances** | 0 | Auto-scales to 0 (free) |

### Environment Variables

Set environment variables in Cloud Run:

```bash
gcloud run services update food-price-anomaly \
  --region us-central1 \
  --set-env-vars LOG_LEVEL=INFO,PYTHONUNBUFFERED=1
```

---

## 📱 Managing Your Deployment

### View Logs

```bash
# Real-time logs
gcloud run services logs read food-price-anomaly \
  --region us-central1 \
  --limit 100 \
  --follow

# View all logs in Cloud Console
# https://console.cloud.google.com/run
```

### Monitor Performance

```bash
# View metrics
gcloud run services describe food-price-anomaly \
  --region us-central1

# Check request metrics
# https://console.cloud.google.com/run/detail/us-central1/food-price-anomaly/metrics
```

### Update Deployment

```bash
# After code changes
git push origin main

# Redeploy
gcloud run deploy food-price-anomaly \
  --source . \
  --region us-central1 \
  --platform managed
```

### Scale Configuration

```bash
# Increase max instances (for more traffic)
gcloud run services update food-price-anomaly \
  --region us-central1 \
  --max-instances 50

# Increase memory
gcloud run services update food-price-anomaly \
  --region us-central1 \
  --memory 4Gi

# Increase CPU
gcloud run services update food-price-anomaly \
  --region us-central1 \
  --cpu 4
```

---

## 🔐 Security & Access Control

### Public Access (Current Setup)

```bash
# Allow unauthenticated access (already set)
gcloud run services add-iam-policy-binding food-price-anomaly \
  --region us-central1 \
  --member allUsers \
  --role roles/run.invoker
```

### Private Access (Restricted)

```bash
# Remove public access
gcloud run services remove-iam-policy-binding food-price-anomaly \
  --region us-central1 \
  --member allUsers \
  --role roles/run.invoker

# Allow specific users/service accounts
gcloud run services add-iam-policy-binding food-price-anomaly \
  --region us-central1 \
  --member user:your-email@gmail.com \
  --role roles/run.invoker
```

---

## 💰 Cost Management

### Free Tier Quotas

```
2 million requests/month
360,000 GB-seconds/month
180,000 vCPU-seconds/month
1 GB egress/month
```

### Estimate Monthly Cost

With current settings:
- Memory: 2Gi × 0.00001234 $/GB-second
- vCPU: 2 × 0.00002400 $/vCPU-second
- Requests: $0.40 per million

**Rough Estimate:** 
- Free tier covers: ~10,000 requests/day
- Beyond free: ~$10-50/month for 100,000 requests/day

### Cost Optimization

```bash
# Reduce max instances during off-hours
gcloud run services update food-price-anomaly \
  --region us-central1 \
  --max-instances 3

# Or use scheduled deployments with Cloud Scheduler
# https://cloud.google.com/scheduler
```

---

## 🐳 Local Testing Before Deploy

### Test Docker Image Locally

```bash
# Build image
docker build -t food-price-anomaly:test .

# Run locally
docker run -p 8501:8501 \
  -e STREAMLIT_SERVER_HEADLESS=true \
  food-price-anomaly:test

# Access at http://localhost:8501
```

### Test with Cloud Run Emulator

```bash
# Install emulator
gcloud components install cloud-run-proxy

# Run local emulator
gcloud run services local --source .
```

---

## 🚢 CI/CD with GitHub & Cloud Build

### Automatic Deployment on Git Push

**Step 1: Connect GitHub Repository**

```bash
# Go to Cloud Build in Cloud Console
# https://console.cloud.google.com/cloud-build/triggers

# Create a new trigger:
# 1. Click "Create Trigger"
# 2. Select GitHub as source
# 3. Authenticate GitHub
# 4. Select repository: lucasWAFULA/Dissertation
# 5. Select branch: main
# 6. Build type: Cloud Run (will use cloudbuild.yaml)
```

**Step 2: Configure cloudbuild.yaml**

File already created in project root.

**Step 3: Deploy Automatically**

Every push to main will:
1. Build Docker image
2. Push to Container Registry
3. Deploy to Cloud Run

---

## 📊 API Backend on Cloud Run

### Deploy FastAPI Backend Separately

Create `Dockerfile.api.gcp`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Deploy:

```bash
gcloud run deploy food-price-api \
  --source . \
  --dockerfile Dockerfile.api.gcp \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --set-env-vars API_WORKERS=4
```

**API URL:** Will be provided in deployment output

---

## 🔗 Connecting UI to API

If deploying API separately:

```bash
# Get API URL
API_URL=$(gcloud run services describe food-price-api \
  --region us-central1 \
  --format 'value(status.url)')

# Set in UI environment variables
gcloud run services update food-price-anomaly \
  --region us-central1 \
  --set-env-vars SCORING_API_URL=$API_URL
```

---

## 🆘 Troubleshooting

### Deployment Fails: "Container failed to start"

```bash
# Check logs
gcloud run services logs read food-price-anomaly \
  --region us-central1 \
  --limit 50

# Common issues:
# 1. Port not 8501 - verify in Dockerfile
# 2. Missing dependencies - check requirements.txt
# 3. Out of memory - increase --memory flag
```

### "Permission denied" errors

```bash
# Ensure APIs are enabled
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Check IAM permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID
```

### Slow Cold Starts

```bash
# Set minimum instances (will cost more)
gcloud run services update food-price-anomaly \
  --region us-central1 \
  --min-instances 1

# Or increase CPU for faster startup
gcloud run services update food-price-anomaly \
  --region us-central1 \
  --cpu 4 \
  --startup-cpu-boost  # Boost CPU during startup
```

### Out of Memory Errors

```bash
# Increase memory
gcloud run services update food-price-anomaly \
  --region us-central1 \
  --memory 4Gi
```

---

## 📈 Monitoring & Alerts

### View Dashboard

```bash
# Open Cloud Console
# https://console.cloud.google.com/run/detail/us-central1/food-price-anomaly
```

### Set Up Alerts

**Via Cloud Console:**
1. Go to Monitoring → Alerting
2. Create Policy → Select Cloud Run service
3. Set threshold (e.g., error rate > 5%)
4. Add notification channel (email/Slack)

**Command line:**

```bash
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Food Price API Errors" \
  --condition-display-name="High Error Rate"
```

---

## 🧹 Cleanup

### Delete Service (Stop Charges)

```bash
gcloud run services delete food-price-anomaly \
  --region us-central1
```

### Delete Images (Free Storage)

```bash
# List images
gcloud container images list --repository=gcr.io/YOUR_PROJECT_ID

# Delete all versions
gcloud container images delete gcr.io/YOUR_PROJECT_ID/food-price-app \
  --quiet
```

---

## 📚 Additional Resources

- **Cloud Run Docs:** https://cloud.google.com/run/docs
- **Pricing Calculator:** https://cloud.google.com/products/calculator
- **Cloud Console:** https://console.cloud.google.com
- **Cloud Build:** https://cloud.google.com/build/docs
- **Container Registry:** https://cloud.google.com/container-registry/docs

---

## 🎯 Next Steps

1. ✅ Create Google Cloud account (free tier)
2. ✅ Install Google Cloud SDK
3. ✅ Run quick deployment command (5 min)
4. ✅ Test your app at provided URL
5. ✅ Monitor costs and performance
6. ✅ Set up CI/CD with GitHub

---

**Status:** Ready for Google Cloud Run deployment! 🚀

For questions, refer to official [Cloud Run documentation](https://cloud.google.com/run/docs) or Google Cloud support.
