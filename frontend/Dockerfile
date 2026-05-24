# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Build React app
# IMPORTANT: VITE_* variables are baked into the static bundle at build time.
# They MUST be passed as --build-arg, not as runtime env vars.
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer-cached)
COPY package.json package-lock.json* ./
RUN npm ci

# Declare build-time Firebase config args
# These are passed by the CI/CD pipeline from GitHub Secrets
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN=marketpulseai-496112.firebaseapp.com
ARG VITE_FIREBASE_PROJECT_ID=marketpulseai-496112
ARG VITE_FIREBASE_STORAGE_BUCKET=marketpulseai-496112.appspot.com
ARG VITE_FIREBASE_MESSAGING_SENDER_ID
ARG VITE_FIREBASE_APP_ID
ARG VITE_API_BASE_URL=https://api.marketpulse.services

# Expose them as environment variables so Vite picks them up during build
ENV VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY
ENV VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN
ENV VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID
ENV VITE_FIREBASE_STORAGE_BUCKET=$VITE_FIREBASE_STORAGE_BUCKET
ENV VITE_FIREBASE_MESSAGING_SENDER_ID=$VITE_FIREBASE_MESSAGING_SENDER_ID
ENV VITE_FIREBASE_APP_ID=$VITE_FIREBASE_APP_ID
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Copy source and build
COPY . .
RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Production server (Express static file server)
# Runtime env vars for the Node server (not Vite) go here
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine

WORKDIR /app

# Run as non-root for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy only what we need
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev

COPY server.js ./
COPY --from=builder /app/dist ./dist

# Runtime environment for the Express proxy
ENV NODE_ENV=production
ENV PORT=3000
# API_BASE_URL is used by server.js to proxy /api/* to the inference service
ENV API_BASE_URL=http://inference-svc:8000

# Drop privileges
USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
