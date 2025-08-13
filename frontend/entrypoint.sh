#!/bin/sh
set -e

# Write runtime config to dist/config.json using VITE_API_BASE_URL
echo "{\n  \"API_BASE_URL\": \"${VITE_API_BASE_URL:-http://localhost:8090}\"\n}" > /app/dist/config.json

exec "$@"