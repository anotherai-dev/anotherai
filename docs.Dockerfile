FROM node:22.8.0-alpine3.20 AS base

# CVEs
RUN apk upgrade libssl3 libcrypto3 libxml2
RUN npm install -g npm@10.9.2 && npm cache clean --force

RUN corepack enable
RUN corepack prepare yarn@stable --activate

FROM base AS sources

WORKDIR /app
COPY .yarnrc.yml ./
COPY .yarn ./.yarn
COPY package.json yarn.lock ./
COPY web/package.json ./web/
# We could optimize here but fumadocs needs the config file and all
# plugins to be loaded during npm ci since it looks for stuff
# in the post install script
COPY docs /app/docs

# Check if lockfile is up to date
RUN yarn install --mode=skip-build --immutable
RUN yarn workspaces focus docs

FROM sources AS dev

EXPOSE 3000
WORKDIR /app/docs

CMD ["yarn", "dev"]

FROM sources AS builder

WORKDIR /app/docs

RUN yarn build

FROM base AS prod

WORKDIR /app

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/docs/.next/standalone ./

USER nextjs
EXPOSE 3000
CMD ["node", "/app/docs/server.js"]

