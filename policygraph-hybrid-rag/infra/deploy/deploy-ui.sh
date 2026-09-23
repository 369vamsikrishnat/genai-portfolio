#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-policygraph-ui}"
API_SERVICE_NAME="${API_SERVICE_NAME:-policygraph-api}"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "Set PROJECT_ID first, for example: export PROJECT_ID=my-project-id" >&2
  exit 1
fi

# Build the image from the repo root.
gcloud builds submit --tag "${IMAGE}" ../..

# Deploy as a separate Cloud Run service.
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 1Gi \
  --min-instances 1 \
  --set-secrets "API_KEY=policygraph-api-key:latest" \
  --set-env-vars "API_URL=https://${API_SERVICE_NAME}-${REGION}.a.run.app" \
  --command python \
  --args "-m,streamlit,run,src/ui/app.py,--server.address,0.0.0.0,--server.port,8501"

printf "\nUI URL: https://%s-%s.a.run.app\n" "${SERVICE_NAME}" "${REGION}"
