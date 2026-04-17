---
name: docker-build
description: Build and tag the tradesensei backend Docker image locally, mirroring the CI workflow for testing before pushing
license: MIT
compatibility: opencode
metadata:
  toolchain: docker, buildx
---

## What I do

Build the multi-stage Alpine-based Docker image locally and verify it matches
what CI would produce, before any code is pushed.

## Image details

| Property | Value |
|----------|-------|
| Base image | `python:3.12-alpine` |
| Build stages | `builder` (gcc + uv install) → `runtime` (minimal) |
| Expected size | ~80–100 MB |
| Registry | `ghcr.io/<owner>/tradesensei-backend` |
| Platforms | `linux/amd64`, `linux/arm64` |

## Quick local build (current platform only)

```bash
# Build for current machine arch (fastest, for local testing)
docker build \
  --tag tradesensei-backend:local \
  --file backend/Dockerfile \
  backend/
```

## Full multi-arch build (mirrors CI)

Requires Docker Buildx with QEMU emulation:

```bash
# One-time setup: create multi-arch builder
docker buildx create --name multiarch --driver docker-container --use
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Build for both platforms (does not push, loads locally)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag tradesensei-backend:local \
  --file backend/Dockerfile \
  backend/ \
  --load
```

Note: `--load` only works for single-platform builds. For multi-arch, use
`--push` to push to a registry, or build each platform separately.

## Verify the image

```bash
# Check image size
docker images tradesensei-backend:local

# Run the container locally
docker run --rm -it \
  --env DATABASE_URL=postgresql+asyncpg://tradesensei:tradesensei@host.docker.internal:5432/tradesensei \
  --env SECRET_KEY=local-dev-secret \
  --env ENVIRONMENT=development \
  -p 8000:8000 \
  tradesensei-backend:local

# Test the health endpoint
curl http://localhost:8000/health
```

## Tag for registry

```bash
# Tagging for ghcr.io (replace <owner> with GitHub username/org)
docker tag tradesensei-backend:local ghcr.io/<owner>/tradesensei-backend:latest
docker tag tradesensei-backend:local ghcr.io/<owner>/tradesensei-backend:dev

# Push (requires docker login to ghcr.io first)
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin
docker push ghcr.io/<owner>/tradesensei-backend:dev
```

## Inspect layers

```bash
# See layer sizes (identify fat layers)
docker history tradesensei-backend:local

# Dive tool for interactive layer inspection (if installed)
dive tradesensei-backend:local
```

## What CI does differently

The `docker.yml` workflow uses:
- `docker/build-push-action` with BuildKit cache (`type=gha`)
- Metadata-generated tags (`:latest`, `:vX.Y.Z`, `:sha-<hash>`)
- Automatic multi-arch builds via QEMU in GitHub Actions runners

Local builds skip the cache and tag manually. Behavior of the application
inside the image is identical.
