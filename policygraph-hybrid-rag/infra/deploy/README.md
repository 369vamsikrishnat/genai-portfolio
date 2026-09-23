# Deployment Notes

This project is designed to run locally with Docker Compose and to be deployed as two separate Cloud Run services: one for the FastAPI service and one for the Streamlit UI.

## Local stack

```bash
docker-compose up --build
```

This starts:
- PostgreSQL with pgvector
- FastAPI app on port 8000
- Streamlit UI on port 8501
- Redis for the semantic cache

## Required environment variables

The app expects the following values in a local `.env` file:

```bash
API_KEY=your-api-key
GEMINI_API_KEY=your-gemini-key
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
LANGFUSE_BASE_URL=https://cloud.langfuse.com
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/policygraph
REDIS_URL=redis://localhost:6379
CACHE_SIMILARITY_THRESHOLD=0.95
CACHE_TTL_SECONDS=86400
```

For Cloud Run, `DATABASE_URL` must be overridden at deploy time to your managed Postgres or Supabase connection string. Do not leave the local `postgres:5432` value in production.

## Health checks

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok","database":"ok"}
```

## Querying the API

```bash
curl -X POST http://localhost:8000/query \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question":"What coverage applies to water damage?"}'
```

## Cloud Run deployment pattern

This project should be deployed as two separate Cloud Run services because the API and UI are separate workloads with different entrypoints.

### API service

```bash
gcloud run deploy policygraph-api \
  --image gcr.io/<PROJECT_ID>/policygraph-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --set-env-vars DATABASE_URL="postgresql://..." \
  --set-secrets API_KEY=api-key:latest,GEMINI_API_KEY=gemini-key:latest \
  --command python \
  --args "-m,uvicorn,src.api.main:app,--host,0.0.0.0,--port,8000"
```

### UI service

```bash
gcloud run deploy policygraph-ui \
  --image gcr.io/<PROJECT_ID>/policygraph-ui \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars API_URL="https://policygraph-api-<hash>-uc.a.run.app" \
  --set-secrets API_KEY=api-key:latest \
  --command python \
  --args "-m,streamlit,run,src/ui/app.py,--server.address,0.0.0.0,--server.port,8501"
```

Important: the Docker image is shared, but the Cloud Run service is not. Each service gets its own URL and its own deploy command.

## Notes

- The API is protected with an `X-API-Key` header.
- The database and Redis are required for retrieval and cache behavior.
- The app expects the ingestion data to sit inside the configured data directory.
- The model warm-up is done during image build to reduce cold start latency; Cloud Run can still be configured with `min-instances=1` if stricter latency is required.

## Production-minded next steps

- Move the Postgres and Redis services to a managed environment.
- Add a secrets manager instead of local `.env` values.
- Split the API and UI into independent deployment targets if the app grows beyond a single project.
- Add a proper reverse proxy and TLS termination for public deployment.
