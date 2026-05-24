# Market Pulse AI — GKE Deployment Runbook

> **Project:** `marketpulseai-496112`  
> **Cluster:** `market-pulse-cluster` · `us-central1`  
> **Domain:** `marketpulse.services`  
> **Registry:** `us-central1-docker.pkg.dev/marketpulseai-496112/market-pulse`

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| `gcloud` CLI | ≥ 460.0 | [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install) |
| `kubectl` | ≥ 1.28 | `gcloud components install kubectl` |
| `docker` | ≥ 24.0 | [docs.docker.com](https://docs.docker.com/get-docker/) |
| `node` | ≥ 20 LTS | [nodejs.org](https://nodejs.org/) |

Log into gcloud:
```bash
gcloud auth login
gcloud auth application-default login
```

---

## Step 1: Run deploy-gke.sh from Cloud Shell

> [!IMPORTANT]
> Run this from Google Cloud Shell or a machine with Owner/Editor IAM permissions on the project.

```bash
# Clone the repo if not already done
git clone https://github.com/YOUR_ORG/market-pulse-ai.git
cd market-pulse-ai

# Make executable
chmod +x deploy-gke.sh

# Dry-run first to preview all commands
./deploy-gke.sh --dry-run

# Execute for real (takes ~10 minutes for cluster creation)
./deploy-gke.sh
```

The script will:
1. Enable all required GCP APIs
2. Create GKE Autopilot cluster (`market-pulse-cluster`)
3. Reserve static IP addresses for prod + staging
4. Create the `market-pulse-deployer` service account with least-privilege roles
5. Download the SA key → `github-actions-key.json`
6. Create Cloud Armor WAF policy (SQLi + XSS + rate limiting)
7. Create empty Secret Manager secrets
8. Configure `kubectl` context
9. Apply base Kubernetes manifests
10. Print the full DNS + GitHub Secrets configuration table

---

## Step 2: Configure Firebase Auth in Console

1. Open [Firebase Console → Authentication](https://console.firebase.google.com/project/marketpulseai-496112/authentication/providers)
2. Click **Get started** if first time
3. Enable **Google** sign-in provider:
   - Set support email to your email
   - Click **Save**
4. Enable **Email/Password** provider → toggle on → **Save**
5. (Optional) Enable **GitHub** OAuth provider with your GitHub OAuth App credentials

---

## Step 3: Get Firebase Web App Config

1. Go to [Firebase Console → Project Settings → General](https://console.firebase.google.com/project/marketpulseai-496112/settings/general)
2. Scroll to **Your apps** → Web app
3. If no web app exists: click **Add app** → Web → register app
4. Copy the config object — you need:
   - `apiKey` → `VITE_FIREBASE_API_KEY`
   - `appId` → `VITE_FIREBASE_APP_ID`
   - `messagingSenderId` → `VITE_FIREBASE_MESSAGING_SENDER_ID`
5. Go to [Project Settings → Service Accounts](https://console.firebase.google.com/project/marketpulseai-496112/settings/serviceaccounts/adminsdk) → **Generate new private key** → download `firebase-service-account.json`

---

## Step 4: Add GitHub Secrets

Go to **GitHub → Repository → Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value | Source |
|-------------|-------|--------|
| `GCP_SA_KEY` | Contents of `github-actions-key.json` | `cat github-actions-key.json` |
| `VITE_FIREBASE_API_KEY` | Firebase Web API Key | Firebase Console → Web App |
| `VITE_FIREBASE_APP_ID` | Firebase App ID | Firebase Console → Web App |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | Sender ID | Firebase Console → Web App |

> [!CAUTION]
> After adding `GCP_SA_KEY` to GitHub, **delete the local `github-actions-key.json` file** — it grants cloud admin access.

```bash
# Add to .gitignore as a safety net
echo "github-actions-key.json" >> .gitignore
rm github-actions-key.json
```

---

## Step 5: Configure DNS at Your Registrar

Point all subdomains to the **static IP** printed by `deploy-gke.sh`:

| Host | Type | Value |
|------|------|-------|
| `app.marketpulse.services` | A | `[PROD_STATIC_IP]` |
| `api.marketpulse.services` | A | `[PROD_STATIC_IP]` |
| `admin.marketpulse.services` | A | `[PROD_STATIC_IP]` |
| `api-staging.marketpulse.services` | A | `[STAGING_STATIC_IP]` |

> [!NOTE]
> GKE Managed Certificates provision automatically once DNS propagates (15-60 min). Monitor with:
> ```bash
> kubectl describe managedcertificate market-pulse-cert -n market-pulse
> ```

Get the static IPs at any time:
```bash
gcloud compute addresses list --global --project=marketpulseai-496112
```

---

## Step 6: Create Kubernetes Secrets

> [!IMPORTANT]
> Do this **before** pushing to main, or the first deploy will fail with missing secret errors.

```bash
# Configure kubectl (if not already done by deploy-gke.sh)
gcloud container clusters get-credentials market-pulse-cluster \
  --region=us-central1 --project=marketpulseai-496112

# Create firebase-secret
kubectl create secret generic firebase-secret \
  --namespace market-pulse \
  --from-literal=credentials-json="$(cat firebase-service-account.json)" \
  --from-literal=web-api-key="YOUR_FIREBASE_WEB_API_KEY" \
  --from-literal=app-id="YOUR_FIREBASE_APP_ID" \
  --from-literal=messaging-sender-id="YOUR_MESSAGING_SENDER_ID"

# Create app-secrets (sentry-dsn is optional)
kubectl create secret generic app-secrets \
  --namespace market-pulse \
  --from-literal=sentry-dsn="YOUR_SENTRY_DSN"

# Create Grafana admin secret
kubectl create secret generic grafana-admin-secret \
  --namespace monitoring \
  --from-literal=admin-user=admin \
  --from-literal=admin-password="YOUR_STRONG_GRAFANA_PASSWORD"
```

---

## Step 7: Push to Main to Trigger First Deploy

```bash
git add -A
git commit -m "chore: production infrastructure setup"
git push origin main
```

Monitor the workflow at:
```
https://github.com/YOUR_ORG/market-pulse-ai/actions
```

The pipeline runs these jobs in order:
1. 🧪 `test-python` — pytest
2. 🔨 `lint-frontend` — npm build validation
3. 🐳 `build-images` — Docker build + push to Artifact Registry
4. 🔒 `security-scan` — vulnerability scan
5. 🚀 `deploy` — apply manifests + rolling update
6. ✅ `verify` — curl health checks
7. 📣 `notify` — step summary

---

## Step 8: Verify Deployment

```bash
# Check pod status
kubectl get pods -n market-pulse
kubectl get pods -n monitoring

# Check ingress and certificate status
kubectl get ingress -n market-pulse
kubectl describe managedcertificate market-pulse-cert -n market-pulse

# Stream inference logs
kubectl logs -f deployment/inference -n market-pulse

# Stream frontend logs
kubectl logs -f deployment/frontend -n market-pulse

# Test endpoints
curl https://api.marketpulse.services/health
curl https://api.marketpulse.services/docs
curl -I https://app.marketpulse.services/
```

Expected `/health` response:
```json
{"status": "healthy", "model_loaded": true}
```

---

## Step 9: Set Up Monitoring (Grafana)

Grafana runs internally on port 3001 in the `monitoring` namespace. Access via port-forward:

```bash
kubectl port-forward svc/grafana-svc 3001:3001 -n monitoring
# Open http://localhost:3001
```

Or expose via the admin subdomain (requires adding a route in the ingress for `/grafana`).

| Setting | Value |
|---------|-------|
| Default URL | `http://localhost:3001` (port-forward) |
| Admin user | `admin` |
| Admin password | Value from `grafana-admin-secret` |
| Prometheus datasource | Auto-provisioned |

Pre-built dashboards to import (by Grafana dashboard ID):
- **1860** — Node Exporter Full
- **6417** — Kubernetes Cluster Monitoring
- Create custom dashboard for Market Pulse inference metrics

---

## Step 10: Create Admin User (Firebase Custom Claims)

To grant admin-level access to a Firebase user, call the admin endpoint with a service account token:

```bash
# Get a token for the admin service account
TOKEN=$(gcloud auth print-identity-token)

# Set custom claim 'role: admin' on a user
curl -X POST https://api.marketpulse.services/admin/set-role \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"uid": "FIREBASE_USER_UID", "role": "admin"}'
```

Or set claims directly via Firebase Admin SDK in a one-time script.

---

## Step 11: Configure Sentry

1. Create a project at [sentry.io](https://sentry.io)
2. Copy your **DSN** from Settings → Client Keys
3. Add to the cluster secret:
   ```bash
   kubectl patch secret app-secrets -n market-pulse \
     --type='json' \
     -p='[{"op":"replace","path":"/data/sentry-dsn","value":"'$(echo -n "YOUR_DSN" | base64)'"}]'
   kubectl rollout restart deployment/inference -n market-pulse
   ```

---

## Troubleshooting

### Pods in CrashLoopBackOff

```bash
kubectl describe pod -l app=inference -n market-pulse
kubectl logs -l app=inference -n market-pulse --previous
```

Common causes:
- Missing Kubernetes secret → create secrets (Step 6)
- PVC not bound → check `kubectl get pvc -n market-pulse`
- Image pull error → verify Artifact Registry permissions

### Certificate Stuck in Provisioning

```bash
kubectl describe managedcertificate market-pulse-cert -n market-pulse
```

- Ensure DNS A records are pointing to the static IP
- Certificate provisioning takes up to 60 minutes after DNS propagates
- Verify with: `nslookup app.marketpulse.services`

### 502 Bad Gateway

```bash
# Check backend service health in GCP Console
gcloud compute backend-services list --global --project=marketpulseai-496112
gcloud compute backend-services get-health BACKEND_SERVICE_NAME --global
```

Common cause: readiness probe failing — check pod logs.

### Cloud Armor Blocking Legitimate Traffic

```bash
# View Cloud Armor logs
gcloud logging read \
  'resource.type="http_load_balancer" jsonPayload.enforcedSecurityPolicy.name="market-pulse-waf-policy"' \
  --project=marketpulseai-496112 \
  --limit=50 \
  --format=json
```

Adjust WAF sensitivity or add IP allowlist rules as needed.

### PVC Fails to Bind (ReadWriteOnce)

If you need multiple write-capable pods, you must either:
1. Use `ReadWriteOnce` with a single writer pod and share data out-of-band, or
2. Upgrade to `Filestore` (NFS) for `ReadWriteMany` semantics

---

## Rollback Procedure

### Automatic Rollback
The CI/CD pipeline automatically rolls back on deployment failure.

### Manual Rollback

```bash
# Roll back to previous inference version
kubectl rollout undo deployment/inference -n market-pulse

# Roll back to a specific revision
kubectl rollout history deployment/inference -n market-pulse
kubectl rollout undo deployment/inference --to-revision=2 -n market-pulse

# Verify rollback
kubectl rollout status deployment/inference -n market-pulse
```

### Image Rollback (specific SHA)

```bash
kubectl set image deployment/inference \
  inference=us-central1-docker.pkg.dev/marketpulseai-496112/market-pulse/inference:PREVIOUS_SHA \
  -n market-pulse
```

---

## Cost Optimization Tips

> [!TIP]
> GKE Autopilot charges per pod resource request — right-sizing matters.

| Optimization | Action |
|--------------|--------|
| **Right-size pods** | Lower inference memory request from 1Gi to 512Mi if P99 usage is lower |
| **Committed Use** | Purchase 1-year CUD for GKE Autopilot compute at ~40% discount |
| **Prometheus retention** | Keep at 7 days (current) — longer retention increases PVC cost |
| **Artifact Registry cleanup** | Add lifecycle policy to delete images older than 30 days |
| **Load balancer** | One GLB covers all 3 subdomains — no extra cost |
| **Cloud Armor** | Standard tier is free for WAF rules; Enterprise tier adds DDoS protection ($3k/mo) |

```bash
# Set Artifact Registry cleanup policy (keep last 10 images per tag)
gcloud artifacts repositories set-cleanup-policies market-pulse \
  --project=marketpulseai-496112 \
  --location=us-central1 \
  --policy='[{"name":"delete-old","action":{"type":"Delete"},"condition":{"newerThan":"30d","tagState":"any"}}]'
```

---

## Architecture Diagram

```
Internet
   │
   ▼
Cloud Armor WAF (market-pulse-waf-policy)
   │  SQLi/XSS rules + rate limiting
   ▼
Google Cloud HTTP(S) Load Balancer
   │  market-pulse-ip (global static)
   │  TLS: GKE ManagedCertificate
   │
   ├─► app.marketpulse.services  ──► frontend-svc:3000  ──► React SPA pods
   ├─► api.marketpulse.services  ──► inference-svc:8000 ──► FastAPI pods
   └─► admin.marketpulse.services ──► frontend-svc:3000 ──► React SPA pods
                                          │
                                          └─► /grafana ──► grafana-svc:3001

GKE Autopilot (market-pulse-cluster, us-central1)
├── Namespace: market-pulse
│   ├── inference Deployment (2 replicas)
│   ├── frontend  Deployment (2 replicas)
│   └── model-data-pvc (5Gi premium-rwo SSD)
└── Namespace: monitoring
    ├── prometheus Deployment + 10Gi PVC
    └── grafana    Deployment + 5Gi PVC

Secrets: Google Secret Manager ──► Kubernetes Secrets ──► Pod env vars
Registry: Artifact Registry (us-central1-docker.pkg.dev/marketpulseai-496112/market-pulse)
CI/CD: GitHub Actions → build → scan → deploy → verify
```
