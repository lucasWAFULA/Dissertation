#!/usr/bin/env bash
# =============================================================================
# deploy-gke.sh — Market Pulse AI — GKE Bootstrap Script
# Project: marketpulseai-496112  Cluster: market-pulse-cluster  Region: us-central1
# =============================================================================
set -euo pipefail

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
PROJECT_ID="marketpulseai-496112"
CLUSTER_NAME="market-pulse-cluster"
REGION="us-central1"
AR_REPO="market-pulse"
SA_NAME="market-pulse-deployer"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
NAMESPACE="market-pulse"
STATIC_IP_NAME="market-pulse-ip"
STAGING_IP_NAME="market-pulse-staging-ip"
WAF_POLICY="market-pulse-waf-policy"
KEY_FILE="github-actions-key.json"

# ─── ANSI COLORS ──────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ─── DRY-RUN FLAG ─────────────────────────────────────────────────────────────
DRY_RUN=false
for arg in "$@"; do
  if [[ "$arg" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  DRY-RUN MODE — no commands will execute     ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════╝${NC}"
  fi
done

# ─── HELPERS ──────────────────────────────────────────────────────────────────
STEP=0

step() {
  STEP=$((STEP + 1))
  echo ""
  echo -e "${BLUE}${BOLD}[Step ${STEP}] $1${NC}"
  echo -e "${BLUE}$(printf '─%.0s' {1..60})${NC}"
}

run() {
  echo -e "${CYAN}  → $*${NC}"
  if [[ "$DRY_RUN" == "false" ]]; then
    eval "$@"
  fi
}

success() {
  echo -e "${GREEN}  ✔ $1${NC}"
}

warn() {
  echo -e "${YELLOW}  ⚠ $1${NC}"
}

error_exit() {
  echo -e "${RED}  ✖ ERROR: $1${NC}" >&2
  exit 1
}

check_prereqs() {
  echo -e "${BOLD}Checking prerequisites...${NC}"
  for cmd in gcloud kubectl; do
    if command -v "$cmd" &>/dev/null; then
      success "$cmd is installed ($(command -v "$cmd"))"
    else
      error_exit "$cmd is not installed. Please install it and re-run."
    fi
  done
}

# ─── BANNER ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          Market Pulse AI — GKE Bootstrap Script              ║"
echo "║  Project: marketpulseai-496112   Region: us-central1         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

check_prereqs

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Set active GCP project
# ─────────────────────────────────────────────────────────────────────────────
step "Set active GCP project"
run "gcloud config set project ${PROJECT_ID}"
success "Project set to ${PROJECT_ID}"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Enable required GCP APIs
# ─────────────────────────────────────────────────────────────────────────────
step "Enable required GCP APIs"
APIS=(
  container.googleapis.com
  artifactregistry.googleapis.com
  firebase.googleapis.com
  secretmanager.googleapis.com
  cloudbuild.googleapis.com
  iam.googleapis.com
  compute.googleapis.com
  cloudresourcemanager.googleapis.com
)
run "gcloud services enable ${APIS[*]} --project=${PROJECT_ID}"
success "All APIs enabled"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Enable Firebase on project
# ─────────────────────────────────────────────────────────────────────────────
step "Enable Firebase on project"
warn "This command requires firebase-tools or gcloud firebase (may fail if already enabled)"
run "gcloud firebase projects:addfirebase ${PROJECT_ID} 2>/dev/null || echo 'Firebase may already be enabled'"
success "Firebase initialization complete"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Create Artifact Registry repository
# ─────────────────────────────────────────────────────────────────────────────
step "Create Artifact Registry repository"
run "gcloud artifacts repositories create ${AR_REPO} \
  --repository-format=docker \
  --location=${REGION} \
  --description='Market Pulse AI container images' \
  --project=${PROJECT_ID} 2>/dev/null || echo 'Repository may already exist'"
success "Artifact Registry repo: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Create GKE Autopilot cluster
# ─────────────────────────────────────────────────────────────────────────────
step "Create GKE Autopilot cluster"
warn "Cluster creation takes 5-10 minutes..."
run "gcloud container clusters create-auto ${CLUSTER_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --release-channel=regular \
  --enable-master-authorized-networks \
  --master-authorized-networks=0.0.0.0/0 \
  2>/dev/null || echo 'Cluster may already exist'"
success "GKE Autopilot cluster: ${CLUSTER_NAME}"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: Reserve global static IP (production)
# ─────────────────────────────────────────────────────────────────────────────
step "Reserve global static IP for production"
run "gcloud compute addresses create ${STATIC_IP_NAME} \
  --global \
  --project=${PROJECT_ID} \
  2>/dev/null || echo 'IP may already be reserved'"
if [[ "$DRY_RUN" == "false" ]]; then
  PROD_IP=$(gcloud compute addresses describe ${STATIC_IP_NAME} --global --format='value(address)' --project=${PROJECT_ID} 2>/dev/null || echo "pending")
  success "Production static IP: ${PROD_IP}"
else
  success "Production static IP: [would be shown here]"
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7: Reserve global static IP (staging)
# ─────────────────────────────────────────────────────────────────────────────
step "Reserve global static IP for staging"
run "gcloud compute addresses create ${STAGING_IP_NAME} \
  --global \
  --project=${PROJECT_ID} \
  2>/dev/null || echo 'Staging IP may already be reserved'"
if [[ "$DRY_RUN" == "false" ]]; then
  STAGING_IP=$(gcloud compute addresses describe ${STAGING_IP_NAME} --global --format='value(address)' --project=${PROJECT_ID} 2>/dev/null || echo "pending")
  success "Staging static IP: ${STAGING_IP}"
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8: Create Service Account with least-privilege roles
# ─────────────────────────────────────────────────────────────────────────────
step "Create GitHub Actions Service Account"
run "gcloud iam service-accounts create ${SA_NAME} \
  --display-name='GitHub Actions Deployer (Market Pulse AI)' \
  --project=${PROJECT_ID} \
  2>/dev/null || echo 'Service account may already exist'"

ROLES=(
  roles/container.developer
  roles/artifactregistry.writer
  roles/secretmanager.secretAccessor
  roles/storage.objectViewer
)
for ROLE in "${ROLES[@]}"; do
  run "gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${SA_EMAIL} \
    --role=${ROLE} \
    --condition=None"
  success "Bound: ${ROLE}"
done

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9: Download Service Account key
# ─────────────────────────────────────────────────────────────────────────────
step "Download Service Account key for GitHub Actions"
if [[ -f "${KEY_FILE}" ]]; then
  warn "${KEY_FILE} already exists — skipping key creation"
else
  run "gcloud iam service-accounts keys create ${KEY_FILE} \
    --iam-account=${SA_EMAIL} \
    --project=${PROJECT_ID}"
  success "Key saved to ${KEY_FILE}"
fi
warn "Add the contents of ${KEY_FILE} as GitHub Secret: GCP_SA_KEY"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 10: Create Cloud Armor WAF policy
# ─────────────────────────────────────────────────────────────────────────────
step "Create Cloud Armor WAF security policy"

run "gcloud compute security-policies create ${WAF_POLICY} \
  --description='WAF policy for Market Pulse AI (OWASP CRS + rate limiting)' \
  --project=${PROJECT_ID} \
  2>/dev/null || echo 'WAF policy may already exist'"

# SQLi rule
run "gcloud compute security-policies rules create 1000 \
  --security-policy=${WAF_POLICY} \
  --expression=\"evaluatePreconfiguredExpr('sqli-stable',{'sensitivity': 1})\" \
  --action=deny-403 \
  --description='Block SQL injection (OWASP CRS sqli-stable)' \
  --project=${PROJECT_ID} \
  2>/dev/null || echo 'SQLi rule may already exist'"
success "Rule 1000: SQLi protection"

# XSS rule
run "gcloud compute security-policies rules create 1001 \
  --security-policy=${WAF_POLICY} \
  --expression=\"evaluatePreconfiguredExpr('xss-stable',{'sensitivity': 1})\" \
  --action=deny-403 \
  --description='Block cross-site scripting (OWASP CRS xss-stable)' \
  --project=${PROJECT_ID} \
  2>/dev/null || echo 'XSS rule may already exist'"
success "Rule 1001: XSS protection"

# Rate limiting rule
run "gcloud compute security-policies rules create 2000 \
  --security-policy=${WAF_POLICY} \
  --expression='true' \
  --action=rate-based-ban \
  --rate-limit-threshold-count=100 \
  --rate-limit-threshold-interval-sec=60 \
  --ban-duration-sec=60 \
  --conform-action=allow \
  --exceed-action=deny-429 \
  --enforce-on-key=IP \
  --description='Rate-limit: 100 req/min per IP, ban 60s on breach' \
  --project=${PROJECT_ID} \
  2>/dev/null || echo 'Rate-limit rule may already exist'"
success "Rule 2000: Rate limiting (100 req/min, ban 60s)"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 11: Create Secret Manager secrets (empty stubs)
# ─────────────────────────────────────────────────────────────────────────────
step "Create Secret Manager secrets (empty stubs)"
SECRETS=(
  firebase-credentials-json
  firebase-web-api-key
  firebase-app-id
  firebase-messaging-sender-id
  sentry-dsn
)
for SECRET in "${SECRETS[@]}"; do
  run "gcloud secrets create ${SECRET} \
    --replication-policy=automatic \
    --project=${PROJECT_ID} \
    2>/dev/null || echo 'Secret ${SECRET} may already exist'"
  success "Secret stub created: ${SECRET}"
done
warn "Fill in secret values via Firebase Console / Sentry and run:"
warn "  echo -n 'VALUE' | gcloud secrets versions add SECRET_NAME --data-file=- --project=${PROJECT_ID}"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 12: Configure kubectl context
# ─────────────────────────────────────────────────────────────────────────────
step "Configure kubectl context"
run "gcloud container clusters get-credentials ${CLUSTER_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID}"
success "kubectl context set to: gke_${PROJECT_ID}_${REGION}_${CLUSTER_NAME}"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 13: Create market-pulse namespace
# ─────────────────────────────────────────────────────────────────────────────
step "Create Kubernetes namespaces"
run "kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -"
run "kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -"
run "kubectl create namespace staging --dry-run=client -o yaml | kubectl apply -f -"
success "Namespaces created: ${NAMESPACE}, monitoring, staging"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 14: Apply base Kubernetes manifests
# ─────────────────────────────────────────────────────────────────────────────
step "Apply base Kubernetes manifests"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run "kubectl apply -f ${SCRIPT_DIR}/k8s/storage/pvc.yaml"
success "PVC: model-data-pvc"

run "kubectl apply -f ${SCRIPT_DIR}/k8s/inference/configmap.yaml"
success "ConfigMap: inference-config"

run "kubectl apply -f ${SCRIPT_DIR}/k8s/ingress/managed-cert.yaml"
run "kubectl apply -f ${SCRIPT_DIR}/k8s/ingress/backend-config.yaml"
run "kubectl apply -f ${SCRIPT_DIR}/k8s/ingress/ingress.yaml"
success "Ingress: managed cert + backend config + ingress rules"

run "kubectl apply -f ${SCRIPT_DIR}/k8s/monitoring/prometheus.yaml"
run "kubectl apply -f ${SCRIPT_DIR}/k8s/monitoring/grafana.yaml"
success "Monitoring: Prometheus + Grafana"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 15: Print deployment summary
# ─────────────────────────────────────────────────────────────────────────────
step "Deployment Summary"

if [[ "$DRY_RUN" == "false" ]]; then
  PROD_IP=$(gcloud compute addresses describe ${STATIC_IP_NAME} --global --format='value(address)' --project=${PROJECT_ID} 2>/dev/null || echo "N/A")
  STAGING_IP=$(gcloud compute addresses describe ${STAGING_IP_NAME} --global --format='value(address)' --project=${PROJECT_ID} 2>/dev/null || echo "N/A")
else
  PROD_IP="[production-ip-here]"
  STAGING_IP="[staging-ip-here]"
fi

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║                  BOOTSTRAP COMPLETE ✔                        ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}📡 Static IP Addresses:${NC}"
echo -e "  Production:  ${GREEN}${PROD_IP}${NC}"
echo -e "  Staging:     ${GREEN}${STAGING_IP}${NC}"
echo ""
echo -e "${BOLD}🌐 DNS Configuration (add at your registrar for marketpulse.services):${NC}"
echo ""
printf "  %-40s %-8s %-15s\n" "HOST" "TYPE" "VALUE"
printf "  %-40s %-8s %-15s\n" "────────────────────────────────────────" "────────" "───────────────"
printf "  %-40s %-8s %-15s\n" "app.marketpulse.services"   "A"     "${PROD_IP}"
printf "  %-40s %-8s %-15s\n" "api.marketpulse.services"   "A"     "${PROD_IP}"
printf "  %-40s %-8s %-15s\n" "admin.marketpulse.services" "A"     "${PROD_IP}"
printf "  %-40s %-8s %-15s\n" "api-staging.marketpulse.services" "A" "${STAGING_IP}"
echo ""
echo -e "${BOLD}🔑 GitHub Secrets to add (Settings → Secrets → Actions):${NC}"
echo ""
printf "  %-40s %s\n" "SECRET NAME" "VALUE SOURCE"
printf "  %-40s %s\n" "────────────────────────────────────────" "────────────────────────────────────"
printf "  %-40s %s\n" "GCP_SA_KEY"                     "Contents of ${KEY_FILE}"
printf "  %-40s %s\n" "VITE_FIREBASE_API_KEY"          "Firebase Console → Project Settings → Web app"
printf "  %-40s %s\n" "VITE_FIREBASE_APP_ID"           "Firebase Console → Project Settings → Web app"
printf "  %-40s %s\n" "VITE_FIREBASE_MESSAGING_SENDER_ID" "Firebase Console → Project Settings → Web app"
echo ""
echo -e "${BOLD}🔥 Firebase Console:${NC}"
echo -e "  ${CYAN}https://console.firebase.google.com/project/${PROJECT_ID}/authentication/providers${NC}"
echo -e "  → Enable: Google Sign-In, Email/Password"
echo ""
echo -e "${BOLD}📋 Next Steps Checklist:${NC}"
echo "  [ ] Add DNS A records at your registrar (see table above)"
echo "  [ ] Visit Firebase Console and enable auth providers"
echo "  [ ] Copy Web App config from Firebase Console"
echo "  [ ] Create kubectl secrets (see k8s/secrets/README.md)"
echo "  [ ] Add GitHub Secrets (see table above)"
echo "  [ ] Push to 'main' branch to trigger first production deploy"
echo "  [ ] Fill in Secret Manager secret values via gcloud CLI"
echo "  [ ] Create Grafana admin secret in 'monitoring' namespace"
echo "      kubectl create secret generic grafana-admin-secret \\"
echo "        --namespace monitoring \\"
echo "        --from-literal=admin-user=admin \\"
echo "        --from-literal=admin-password='YOUR_STRONG_PASSWORD'"
echo ""
echo -e "${YELLOW}${BOLD}⚠  SECURITY REMINDER:${NC}"
echo -e "${YELLOW}  - Do NOT commit ${KEY_FILE} to Git (it's in .gitignore)${NC}"
echo -e "${YELLOW}  - Delete the local key file after adding it to GitHub Secrets${NC}"
echo -e "${YELLOW}  - Rotate the service account key every 90 days${NC}"
echo ""
