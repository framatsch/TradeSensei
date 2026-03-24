FROM node:20-alpine AS base

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci --legacy-peer-deps

FROM base AS development

ENV NODE_ENV=development

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]

FROM base AS builder

ENV NODE_ENV=production

COPY . .

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

EXPOSE 3000

CMD ["node", "server.js"]
