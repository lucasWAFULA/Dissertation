#!/bin/bash

# Google Cloud Run Deployment Script
# Usage: ./deploy-gcloud.sh YOUR_PROJECT_ID

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check arguments
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide Google Cloud Project ID${NC}"
    echo "Usage: ./deploy-gcloud.sh YOUR_PROJECT_ID"
    exit 1
fi

PROJECT_ID=$1
REGION=${2:-us-central1}
SERVICE_NAME="food-price-anomaly"

echo -e "${GREEN}=== Google Cloud Run Deployment ===${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Step 1: Check if gcloud is installed
echo -e "${YELLOW}[1/6] Checking Google Cloud SDK...${NC}"
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not installed${NC}"
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi
echo -e "${GREEN}✓ gcloud CLI found${NC}"

# Step 2: Set project
echo -e "${YELLOW}[2/6] Setting Google Cloud project...${NC}"
gcloud config set project $PROJECT_ID
echo -e "${GREEN}✓ Project set to $PROJECT_ID${NC}"

# Step 3: Enable APIs
echo -e "${YELLOW}[3/6] Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
echo -e "${GREEN}✓ APIs enabled${NC}"

# Step 4: Build and push image
echo -e "${YELLOW}[4/6] Building Docker image...${NC}"
gcloud builds submit \
  --config cloudbuild.yaml \
  --project=$PROJECT_ID \
  --substitutions="_REGION=$REGION,_SERVICE_NAME=$SERVICE_NAME"
echo -e "${GREEN}✓ Image built and pushed${NC}"

# Step 5: Deploy to Cloud Run
echo -e "${YELLOW}[5/6] Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/food-price-app:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars="LOG_LEVEL=INFO,PYTHONUNBUFFERED=1" \
  --project=$PROJECT_ID
echo -e "${GREEN}✓ Deployment complete${NC}"

# Step 6: Get service URL
echo -e "${YELLOW}[6/6] Retrieving service URL...${NC}"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format 'value(status.url)' \
  --project=$PROJECT_ID)

echo ""
echo -e "${GREEN}=== Deployment Successful ===${NC}"
echo ""
echo -e "${GREEN}Your application is live at:${NC}"
echo -e "${YELLOW}$SERVICE_URL${NC}"
echo ""
echo "Next steps:"
echo "1. Open: $SERVICE_URL"
echo "2. View logs: gcloud run services logs read $SERVICE_NAME --region $REGION"
echo "3. View metrics: https://console.cloud.google.com/run"
echo ""
