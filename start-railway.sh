#!/bin/bash

# Set default port if not provided by Railway
export PORT=${PORT:-3000}

# Start FastAPI backend in background
uvicorn main:app --host 127.0.0.1 --port 8000 &

# Replace $PORT in nginx config template with actual PORT value
envsubst '$PORT' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Start nginx in foreground
nginx -g "daemon off;"