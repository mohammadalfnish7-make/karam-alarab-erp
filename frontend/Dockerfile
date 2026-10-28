# syntax=docker/dockerfile:1

# --- build SPA --------------------------------------------------------------
FROM node:24-bookworm-slim AS build

WORKDIR /app

COPY package.json package-lock.json .npmrc ./
RUN npm ci

COPY index.html vite.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY public ./public
COPY src ./src

# Same-origin /api in the image (nginx proxies to the API service).
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# --- serve static + proxy /api ---------------------------------------------
FROM nginx:1.28-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
