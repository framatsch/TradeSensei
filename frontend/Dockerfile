FROM node:20-alpine AS base

WORKDIR /app

# Build context is the repo root — copy only frontend deps first for layer caching
COPY frontend/package.json frontend/package-lock.json ./

RUN npm ci --legacy-peer-deps

FROM base AS development

ENV NODE_ENV=development

# In docker-compose the source is bind-mounted over /app, so this COPY is only
# a fallback for bare `docker build --target development` invocations.
COPY frontend/ .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]

FROM base AS builder

ENV NODE_ENV=production

# Copy frontend source
COPY frontend/ .
# Copy root logo.svg into public/ so it is the single source of truth
COPY logo.svg ./public/logo.svg

RUN npm run build

FROM node:20-alpine AS production

ARG GITHUB_REPOSITORY
ENV GITHUB_REPOSITORY=${GITHUB_REPOSITORY}
LABEL org.opencontainers.image.source=https://github.com/${GITHUB_REPOSITORY}

WORKDIR /app

ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
COPY frontend/docker-entrypoint.sh ./docker-entrypoint.sh

EXPOSE 3000

CMD ["sh", "docker-entrypoint.sh"]
