# Kubernetes Secrets

Secrets are **never stored in this repository**.

## Required Secrets

Create these secrets manually in the `tradesensei` namespace before deploying.

### `backend-secrets`

Contains sensitive backend configuration:

```bash
kubectl create secret generic backend-secrets \
  --namespace tradesensei \
  --from-literal=DB_USER='tradesensei' \
  --from-literal=DB_PASSWORD='<strong-password>' \
  --from-literal=SECRET_KEY='<random-256-bit-key>'
```

Optional alternative:

```bash
kubectl create secret generic backend-secrets \
  --namespace tradesensei \
  --from-literal=DATABASE_URL='postgresql+asyncpg://user:pass@timescaledb:5432/tradesensei' \
  --from-literal=SECRET_KEY='<random-256-bit-key>'
```

### `frontend-secrets`

Contains sensitive frontend runtime configuration:

```bash
kubectl create secret generic frontend-secrets \
  --namespace tradesensei \
  --from-literal=NEXTAUTH_SECRET='<random-32-byte-secret>' \
  --from-literal=NEXT_PUBLIC_GOOGLE_CLIENT_ID=''
```

### `db-credentials`

PostgreSQL superuser credentials used by the TimescaleDB StatefulSet:

```bash
kubectl create secret generic db-credentials \
  --namespace tradesensei \
  --from-literal=username='tradesensei' \
  --from-literal=password='<strong-password>'
```

### `ghcr-credentials`

Docker pull secret for the GitHub Container Registry:

```bash
kubectl create secret docker-registry ghcr-credentials \
  --namespace tradesensei \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<github-pat> \
  --docker-email=<email>
```

### `tls-backend`

TLS certificate for the backend Ingress (`api.tradesensei.example.com`).
Managed by cert-manager if installed, or created manually:

```bash
kubectl create secret tls tls-backend \
  --namespace tradesensei \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key
```

### `tls-frontend`

TLS certificate for the frontend Ingress (`tradesensei.example.com`):

```bash
kubectl create secret tls tls-frontend \
  --namespace tradesensei \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key
```

## Security Notes

- Rotate `SECRET_KEY` and database passwords periodically.
- Use a secrets manager (e.g. HashiCorp Vault, AWS Secrets Manager) in
  production rather than kubectl-created secrets.
- Never commit `.env` files, `*.pem` files, or any file containing credentials.
- GitHub Actions uses repository secrets (`Settings → Secrets and variables`);
  map them to `GHCR_TOKEN`, `KUBE_CONFIG`, etc.
