# Multi-stage Dockerfile for Railway deployment
FROM node:18-alpine as frontend-builder

# Build frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Python backend stage
FROM python:3.11-slim

# Install system dependencies including gettext for envsubst
RUN apt-get update && apt-get install -y \
    nginx \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend
COPY --from=frontend-builder /app/frontend/build ./static

# Copy nginx configuration template
COPY nginx-railway.conf /etc/nginx/nginx.conf.template

# Copy startup script
COPY start-railway.sh ./
RUN chmod +x start-railway.sh

# Expose port (Railway will provide PORT environment variable)
EXPOSE 3000

# Start script
CMD ["./start-railway.sh"]