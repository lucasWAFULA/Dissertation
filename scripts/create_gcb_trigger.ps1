param(
  [string]$ProjectId = 'marketpulseai-496112',
  [string]$RepoOwner = 'lucasWAFULA',
  [string]$RepoName = 'Dissertation',
  [string]$TriggerName = 'food-price-anomaly-trigger'
)

Write-Host "Creating Cloud Build GitHub trigger: $TriggerName for $RepoOwner/$RepoName in project $ProjectId"

gcloud beta builds triggers create github `
  --name="$TriggerName" `
  --repo-owner="$RepoOwner" `
  --repo-name="$RepoName" `
  --branch-pattern="^main$" `
  --build-config="cloudbuild.yaml" `
  --project="$ProjectId"

Write-Host "Done - visit Cloud Console > Cloud Build > Triggers to verify."
