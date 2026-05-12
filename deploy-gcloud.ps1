# Google Cloud Run Deployment Script for Windows PowerShell
# Usage: .\deploy-gcloud.ps1 -ProjectId YOUR_PROJECT_ID

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    
    [string]$Region = "us-central1",
    [string]$ServiceName = "food-price-anomaly"
)

$ErrorActionPreference = "Stop"

# Colors
$Green = @{ ForegroundColor = "Green" }
$Yellow = @{ ForegroundColor = "Yellow" }
$Red = @{ ForegroundColor = "Red" }

Write-Host "=== Google Cloud Run Deployment ===" @Green
Write-Host "Project ID: $ProjectId"
Write-Host "Region: $Region"
Write-Host "Service: $ServiceName"
Write-Host ""

# Step 1: Check if gcloud is installed
Write-Host "[1/6] Checking Google Cloud SDK..." @Yellow
try {
    $gcloudVersion = gcloud --version 2>$null
    Write-Host "✓ gcloud CLI found" @Green
} catch {
    Write-Host "Error: gcloud CLI not installed" @Red
    Write-Host "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
}

# Step 2: Set project
Write-Host "[2/6] Setting Google Cloud project..." @Yellow
gcloud config set project $ProjectId
Write-Host "✓ Project set to $ProjectId" @Green

# Step 3: Enable APIs
Write-Host "[3/6] Enabling required APIs..." @Yellow
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
Write-Host "✓ APIs enabled" @Green

# Step 4: Build and push image
Write-Host "[4/6] Building Docker image..." @Yellow
gcloud builds submit `
  --config cloudbuild.yaml `
  --project=$ProjectId `
  --substitutions "_REGION=$Region,_SERVICE_NAME=$ServiceName"
Write-Host "✓ Image built and pushed" @Green

# Step 5: Deploy to Cloud Run
Write-Host "[5/6] Deploying to Cloud Run..." @Yellow
gcloud run deploy $ServiceName `
  --image "gcr.io/$ProjectId/food-price-app:latest" `
  --platform managed `
  --region $Region `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300 `
  --max-instances 10 `
  --set-env-vars="LOG_LEVEL=INFO,PYTHONUNBUFFERED=1" `
  --project=$ProjectId
Write-Host "✓ Deployment complete" @Green

# Step 6: Get service URL
Write-Host "[6/6] Retrieving service URL..." @Yellow
$ServiceUrl = gcloud run services describe $ServiceName `
  --region $Region `
  --format 'value(status.url)' `
  --project=$ProjectId

Write-Host ""
Write-Host "=== Deployment Successful ===" @Green
Write-Host ""
Write-Host "Your application is live at:" @Green
Write-Host $ServiceUrl @Yellow
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Open: $ServiceUrl"
Write-Host "2. View logs: gcloud run services logs read $ServiceName --region $Region"
Write-Host "3. View metrics: https://console.cloud.google.com/run"
Write-Host ""
