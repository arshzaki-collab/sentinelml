# ==============================================================================
# BLIND BILLION 2.0 — FRONTEND DOCKERFILE
# Multi-stage production container with Vite build and static server
# ==============================================================================

FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS serve

WORKDIR /app

RUN npm install -g serve

COPY --from=build /app/dist /app/dist

EXPOSE 5173

CMD ["serve", "-s", "dist", "-l", "5173"]
