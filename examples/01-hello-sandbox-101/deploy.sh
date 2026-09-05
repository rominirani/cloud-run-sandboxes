#!/usr/bin/env bash
set -euo pipefail

# Configuration defaults
SERVICE_NAME=${SERVICE_NAME:-"sandbox-hello-101"}
REGION=${REGION:-"us-central1"}
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}

echo "=========================================================="
echo "Deploying Cloud Run Sandbox Service: ${SERVICE_NAME}"
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo "=========================================================="

# Deploy service with the --sandbox-launcher flag enabled
# Note: Requires gcloud beta components and second-generation execution environment
gcloud beta run deploy "${SERVICE_NAME}" \
    --source . \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --execution-environment gen2 \
    --sandbox-launcher \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1

echo "Deployment complete! Fetching service URL..."
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --project "${PROJECT_ID}" --format='value(status.url)')
echo "Service deployed at: ${SERVICE_URL}"
echo ""
echo "Test the service with:"
echo "curl -X POST ${SERVICE_URL}/run -H 'Content-Type: application/json' -d '{\"language\": \"python\", \"code\": \"print(1+1)\"}'"
