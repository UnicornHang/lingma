# LingMa Frontend Dockerfile
# Multi-stage build: Node for build, Nginx for serving

# ==================== Stage 1: Build ====================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
# (Use npm ci if package-lock.json exists, otherwise npm install)
RUN npm install --no-audit --no-fund

# Copy source
COPY . .

# Build arguments for API endpoint
ARG VITE_API_BASE=/api/v1
ENV VITE_API_BASE=$VITE_API_BASE

# Build
RUN npm run build

# ==================== Stage 2: Runtime ====================
FROM nginx:1.25-alpine AS runtime

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]