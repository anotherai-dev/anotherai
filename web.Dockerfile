FROM node:22.8.0-alpine3.20 AS base

# CVEs
RUN apk upgrade libssl3 libcrypto3 libxml2
RUN npm install -g npm@10.9.2 && npm cache clean --force

FROM base AS deps

WORKDIR /app
COPY package.json package-lock.json ./
COPY web/package.json ./web/

# Install all dependencies
# Next JS needs dev dependencies 
RUN npm ci --include=dev --include=prod 

FROM deps AS sources

WORKDIR /app

COPY web /app/web
COPY --from=deps /app/package.json /app/package-lock.json ./
COPY --from=deps /app/web/package.json ./web

FROM sources AS dev

EXPOSE 3000
WORKDIR /app/web

CMD ["npx", "next", "dev"]

FROM sources AS builder

WORKDIR /app/web

RUN npm run build

FROM base AS prod

WORKDIR /app

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/web/.next/standalone ./

USER nextjs
EXPOSE 3000
CMD ["node", "/app/web/server.js"]

