# ── Stage 1: build the React app ─────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies (cached unless package files change)
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Bake env vars into the static bundle at build time.
# VITE_API_BASE_URL=/api means the browser calls /api/... which Nginx proxies
# to the api container — no CORS, same origin.
ARG VITE_API_BASE_URL=/api
ARG VITE_AUTH_MODE=local
ARG VITE_LOCAL_USER_ID=dev-user

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_AUTH_MODE=$VITE_AUTH_MODE \
    VITE_LOCAL_USER_ID=$VITE_LOCAL_USER_ID

RUN npm run build

# ── Stage 2: serve with Nginx ─────────────────────────────────────────────────
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
