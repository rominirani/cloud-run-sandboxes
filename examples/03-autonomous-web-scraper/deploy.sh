#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME=${SERVICE_NAME:-"sandbox-web-scraper"}
REGION=${REGION:-"us-central1"}
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}

echo "Deploying Autonomous Web Scraper to Cloud Run Sandboxes..."
gcloud beta run deploy "${SERVICE_NAME}" \
    --source . \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --execution-environment gen2 \
    --sandbox-launcher \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1

echo "Deployment finished!"
