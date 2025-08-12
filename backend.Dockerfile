# Build stage
ARG PYTHON_VERSION=3.13
ARG ALPINE_VERSION=3.22
ARG ARCH=linux/amd64
ARG RELEASE_NAME=

FROM --platform=${ARCH} python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS base

# ffmpeg is needed for audio processing
# poppler is needed for pdf processing
# Other upgrades are due for CVEs
RUN apk update && \
    apk add --no-cache ffmpeg poppler-utils sqlite-libs>=3.48.0-r3 && \
    apk upgrade --available --no-cache libssl3 libcrypto3 libxml2 xz-libs

# Builder stage
# Instals the dependencies via uv and copies the source code
FROM base AS builder

RUN apk add --no-cache build-base libffi-dev geos-dev

ENV UV_COMPILE_BYTECODE=1  UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.4.9 /uv /bin/uv

WORKDIR /app

COPY uv.lock pyproject.toml /app/
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-install-project --no-dev

COPY backend/core /app/core
COPY backend/protocol /app/protocol
COPY docs /app/docs


RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Production stage
FROM base

COPY --from=builder /app /app
ENV JSON_LOGS=1
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
WORKDIR /app

CMD ["uvicorn", "protocol.api.api_server:api", "--host", "0.0.0.0", "--port", "8000"]
