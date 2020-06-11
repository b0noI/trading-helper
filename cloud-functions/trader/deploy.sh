#!/usr/bin/env bash

gcloud functions deploy trade  \
    --region us-central1 \
    --project trading-systems-252219 \
    --entry-point trade \
    --runtime python37 \
    --memory 512 \
    --trigger-topic "trade-signals" \
    --service-account trader@trading-systems-252219.iam.gserviceaccount.com
