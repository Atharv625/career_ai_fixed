# ── Stage 1: Build ───────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy manifests first for better layer caching
COPY package*.json ./

# Use production install but with devDependencies (needed for Vite)
# NODE_ENV=development keeps devDeps; we strip them in the nginx stage
ENV NODE_ENV=development
RUN npm ci --prefer-offline

COPY . .

# Bake the API URL into the static bundle at build time
# Override via --build-arg or docker-compose build args
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ── Stage 2: Serve ───────────────────────────────────────────
FROM nginx:1.25-alpine
COPY data ./data

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
