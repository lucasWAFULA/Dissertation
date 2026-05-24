# Kubernetes Secrets — Market Pulse AI

> ⚠️ **NEVER commit secrets to Git.** This directory contains NO secret values.
> All sensitive credentials are managed via **Google Secret Manager** and injected
> into the cluster with `kubectl create secret`. The `.gitignore` at repo root
> already excludes `*.json` and `*-key.*` files.

---

## Secret Architecture

```
Google Secret Manager          Kubernetes Cluster
───────────────────────────    ──────────────────────────────────
firebase-credentials-json  ──► firebase-secret / credentials-json
firebase-web-api-key       ──► firebase-secret / web-api-key
firebase-app-id            ──► firebase-secret / app-id
firebase-messaging-sender  ──► firebase-secret / messaging-sender-id
sentry-dsn                 ──► app-secrets     / sentry-dsn
```

---

## Creating Secrets in the Cluster

Run these commands **once** after the cluster is bootstrapped (deploy-gke.sh handles
the Secret Manager side; the commands below populate Kubernetes secrets):

### `firebase-secret`

```bash
# Create firebase-secret
kubectl create secret generic firebase-secret \
  --namespace market-pulse \
  --from-literal=credentials-json="$(cat firebase-service-account.json)" \
  --from-literal=web-api-key="YOUR_FIREBASE_WEB_API_KEY" \
  --from-literal=app-id="YOUR_FIREBASE_APP_ID" \
  --from-literal=messaging-sender-id="YOUR_MESSAGING_SENDER_ID"
```

> **Where to get values:**
> - `firebase-service-account.json` — Firebase Console → Project Settings → Service Accounts → Generate new private key
> - `web-api-key` — Firebase Console → Project Settings → General → Your apps → Web API Key
> - `app-id` — Firebase Console → Project Settings → General → Your apps → App ID
> - `messaging-sender-id` — Firebase Console → Project Settings → General → Your apps → Sender ID

### `app-secrets`

```bash
# Create app-secrets
kubectl create secret generic app-secrets \
  --namespace market-pulse \
  --from-literal=sentry-dsn="YOUR_SENTRY_DSN"
```

> **Where to get values:**
> - `sentry-dsn` — Sentry.io → Your Project → Settings → Client Keys (DSN)

---

## Staging Namespace

Repeat the same commands with `--namespace staging` for the staging environment.

---

## Rotating Secrets

```bash
# Update a single key inside an existing secret
kubectl patch secret firebase-secret \
  --namespace market-pulse \
  --type='json' \
  -p='[{"op":"replace","path":"/data/web-api-key","value":"'$(echo -n "NEW_API_KEY" | base64)'"}]'

# Restart deployments to pick up the new secret
kubectl rollout restart deployment/inference deployment/frontend -n market-pulse
```

---

## Verifying Secrets Exist

```bash
# List secrets in the namespace
kubectl get secrets -n market-pulse

# Describe (shows keys but NOT values)
kubectl describe secret firebase-secret -n market-pulse
kubectl describe secret app-secrets -n market-pulse
```

---

## Google Secret Manager Reference

```bash
# View current version of a secret (requires secretmanager.secretAccessor role)
gcloud secrets versions access latest --secret="firebase-web-api-key" --project=marketpulseai-496112

# Add a new version (rotation)
echo -n "NEW_VALUE" | gcloud secrets versions add firebase-web-api-key \
  --data-file=- --project=marketpulseai-496112
```
