#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-policygraph-api}"
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
  --memory 2Gi \
  --min-instances 1 \
  --set-secrets "API_KEY=policygraph-api-key:latest,GEMINI_API_KEY=policygraph-gemini-key:latest,LANGFUSE_PUBLIC_KEY=policygraph-langfuse-public-key:latest,LANGFUSE_SECRET_KEY=policygraph-langfuse-secret-key:latest,DATABASE_URL=policygraph-db-url:latest" \
  --set-env-vars "LANGFUSE_BASE_URL=https://cloud.langfuse.com,CACHE_SIMILARITY_THRESHOLD=0.95,CACHE_TTL_SECONDS=86400,MAX_QUESTION_LENGTH=2000,MAX_SOURCE_LENGTH=255" \
  --command python \
  --args "-m,uvicorn,src.api.main:app,--host,0.0.0.0,--port,8000"

printf "\nAPI URL: https://%s-%s.a.run.app\n" "${SERVICE_NAME}" "${REGION}"
