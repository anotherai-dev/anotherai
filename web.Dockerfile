FROM node:22.8.0-alpine3.20 AS base

# CVEs
RUN apk upgrade libssl3 libcrypto3 libxml2
RUN npm install -g npm@10.9.2 && npm cache clean --force

RUN corepack enable
RUN corepack prepare yarn@stable --activate

# Accept build arguments
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=''
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}

FROM base AS deps

WORKDIR /app
COPY package.json yarn.lock ./
COPY web/package.json ./web/
COPY docs/package.json ./docs/

# Check if locfile is up to date
RUN yarn install --mode=skip-build --immutable
# Install only the web dependencies
RUN yarn workspaces focus web

FROM deps AS sources

WORKDIR /app

COPY web /app/web
COPY --from=deps /app/package.json /app/yarn.lock ./
COPY --from=deps /app/web/package.json ./web

FROM sources AS dev

EXPOSE 3000
WORKDIR /app/web

CMD ["yarn", "run", "next", "dev"]


FROM sources AS builder

WORKDIR /app/web

RUN yarn build

FROM base AS prod

WORKDIR /app

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/web/.next/standalone ./

USER nextjs
EXPOSE 3000
CMD ["node", "/app/web/server.js"]

