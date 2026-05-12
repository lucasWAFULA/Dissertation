#!/bin/bash
set -euo pipefail

# Create a GitHub -> Cloud Build trigger for this repository.
# Usage: ./scripts/create_gcb_trigger.sh [PROJECT_ID] [REPO_OWNER] [REPO_NAME] [TRIGGER_NAME]
# Example: ./scripts/create_gcb_trigger.sh marketpulseai-496112 lucasWAFULA Dissertation food-price-anomaly-trigger

PROJECT_ID=${1:-marketpulseai-496112}
REPO_OWNER=${2:-lucasWAFULA}
REPO_NAME=${3:-Dissertation}
TRIGGER_NAME=${4:-food-price-anomaly-trigger}

echo "Creating Cloud Build GitHub trigger: $TRIGGER_NAME for $REPO_OWNER/$REPO_NAME in project $PROJECT_ID"

gcloud beta builds triggers create github \
  --name="$TRIGGER_NAME" \
  --repo-owner="$REPO_OWNER" \
  --repo-name="$REPO_NAME" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --project="$PROJECT_ID"

echo "Done — visit Cloud Console > Cloud Build > Triggers to verify."
