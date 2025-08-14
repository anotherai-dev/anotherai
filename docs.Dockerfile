FROM node:22.8.0-alpine3.20 AS base

# CVEs
RUN apk upgrade libssl3 libcrypto3 libxml2
RUN npm install -g npm@10.9.2 && npm cache clean --force

FROM base AS sources

WORKDIR /app
COPY package.json package-lock.json ./
# We could optimze here but fumadocs needs the config file and all
# plugins to be loaded during npm ci since it looks for stuff
# in the post install script
COPY docs /app/docs

# Install all dependencies
# Next JS needs dev dependencies 
RUN npm ci --include=dev --include=prod 

FROM sources AS dev

EXPOSE 3000
WORKDIR /app/docs

CMD ["npx", "next", "dev"]

FROM sources AS builder

WORKDIR /app/docs

RUN npm run build

FROM base AS prod

WORKDIR /app

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/docs/.next/standalone ./

USER nextjs
EXPOSE 3000
CMD ["node", "/app/docs/server.js"]

