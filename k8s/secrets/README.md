# Kubernetes Secrets

Secrets are **never stored in this repository**.

## Required Secrets

Create these secrets manually in the `tradejournal` namespace before deploying.

### `backend-secrets`

Contains sensitive backend configuration:

```bash
kubectl create secret generic backend-secrets \
  --namespace tradejournal \
  --from-literal=DATABASE_URL='postgresql+asyncpg://user:pass@timescaledb:5432/tradejournal' \
  --from-literal=SECRET_KEY='<random-256-bit-key>'
```

### `db-credentials`

PostgreSQL superuser credentials used by the TimescaleDB StatefulSet:

```bash
kubectl create secret generic db-credentials \
  --namespace tradejournal \
  --from-literal=username='tradejournal' \
  --from-literal=password='<strong-password>'
```

### `ghcr-credentials`

Docker pull secret for the GitHub Container Registry:

```bash
kubectl create secret docker-registry ghcr-credentials \
  --namespace tradejournal \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<github-pat> \
  --docker-email=<email>
```

### `tls-backend`

TLS certificate for the backend Ingress (`api.tradejournal.example.com`).
Managed by cert-manager if installed, or created manually:

```bash
kubectl create secret tls tls-backend \
  --namespace tradejournal \
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
