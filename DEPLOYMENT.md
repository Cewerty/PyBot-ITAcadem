# Deployment

This repository now includes a production deployment skeleton that extends the existing CI without changing the current `CI - Code Quality` or `Release` workflows.

## What was added

- `docker-compose.prod.yml` for immutable image-based production deploys
- `.github/workflows/deploy.yml` for build + push + deploy after successful CI on `main`, plus manual recovery redeploys from GitHub Actions
- `ansible/` with a minimal bootstrap/deploy playbook and roles

The CI workflow also validates the Docker build, both Compose manifests, and the `fill_point_db.py` CLI help entrypoint before code reaches production deploy.

## Deployment flow

1. A push reaches `main`, or an operator manually starts the production workflow from GitHub Actions on `main`.
2. Existing CI runs and must finish successfully for the automatic path.
3. `CD - Build and Deploy` starts either from `workflow_run` or `workflow_dispatch`.
4. GitHub Actions builds a Docker image and pushes it to GHCR.
5. GitHub Actions runs Ansible against the target server.
6. Ansible copies `docker-compose.prod.yml` and `.env` into the deploy user's workspace, runs the one-shot `migrate` process, optionally runs the one-shot `seed` process, and only then starts the runtime services.
7. Ansible runs a lightweight post-deploy smoke-check: it verifies that the core runtime services appear in `docker compose ps` and waits for Redis health when a healthcheck is present.

## Manual redeploy

If you need to redeploy the current `main` release without creating an empty commit:

1. Open `Actions` in GitHub.
2. Choose `CD - Build and Deploy`.
3. Click `Run workflow`.
4. Run it from the `main` branch.

This is useful for recovery, token rotation, or controlled re-runs after infrastructure-side fixes.

## Why production uses a separate compose file

`docker-compose.yml` remains the local/dev entrypoint and still builds from source.

`docker-compose.prod.yml` is intentionally image-based:

- the server does not need the git repository checked out;
- the deployment uses an immutable image tag;
- the deploy host only needs Docker, Compose, `.env`, and persistent volumes.
- both local and production Compose files keep the same process model while differing only in build source (`build` vs `image`).

## Shared Compose process model

Both `docker-compose.yml` and `docker-compose.prod.yml` describe the same operational shape:

- default runtime process types: `bot`, `taskiq-worker`, `taskiq-scheduler`, `redis`
- optional runtime process type: `health` behind the `health` profile
- admin one-shot process type: `migrate` behind the `migration` profile
- admin one-shot process type: `seed` behind the `seed` profile

That alignment is deliberate:

- Factor X Dev/Prod parity: local and production use the same process model
- Factor V Build/Release/Run: runtime processes stay separate from admin one-shot steps
- Factor VI Processes: each process type has an explicit entrypoint instead of hidden startup side effects

Worker concurrency follows the same env-driven mechanism in dev and prod: `taskiq-worker` reads `${TASKIQ_WORKERS:-1}` from Compose. This is a 12-factor uplift step, but the current runtime still intentionally supports only `TASKIQ_WORKERS=1`; larger values fail fast until multi-instance readiness work is completed.

## Required GitHub secrets

Configure these in the `production` environment or repository secrets:

- `DEPLOY_HOST` - server IP or DNS name
- `DEPLOY_USER` - SSH user used by Ansible
- `DEPLOY_SSH_KEY` - private SSH key for the deploy user
- `DEPLOY_KNOWN_HOSTS` - pinned `known_hosts` entry for the server
- `PROD_ENV_FILE` - full multiline production `.env` file contents

Optional secrets:

- `DEPLOY_PORT` - SSH port, defaults to `22`
- `DEPLOY_PATH` - application directory on the server, defaults to `/home/ilya/pybot`
- `GHCR_DEPLOY_USERNAME` - username for pulling private GHCR images on the server
- `GHCR_DEPLOY_TOKEN` - token for pulling private GHCR images on the server
- `RUN_SEED_ON_DEPLOY` - set to `true` only for the initial deploy when you need to run `fill_point_db.py`

## Expected server shape

The regular CD deploy assumes:

- Docker is already installed on the server
- the deploy user can run Docker commands without `sudo`
- the deploy path is writable by the deploy user

An optional bootstrap playbook is still available for Debian/Ubuntu hosts:

- [`ansible/playbooks/bootstrap.yml`](/e:/StudBot/PyBot_ITAcadem/ansible/playbooks/bootstrap.yml#L1)
- it installs `docker.io` and `docker-compose-plugin`
- it is intentionally separate from the normal CD path so routine deploys do not mutate shared server infrastructure

The app is deployed into `/home/ilya/pybot` by default and keeps persistent data in named Docker volumes:

- `pybot_data_prod`
- `pybot_redis_data_prod`

The deploy also persists the currently released image reference as `APP_IMAGE` inside the server-side `.env`, so routine manual commands like `docker compose ps` and `docker compose logs` work without extra exports.

When SQLite is used in production, the backup step now derives the backup target from `DATABASE_URL` as long as it points under `./data/...`, so backup behavior stays aligned with the configured database filename.

## Notes about ports

`docker-compose.prod.yml` does publish host ports only for the reverse-proxy entrypoint.

That means:

- Redis stays internal to the Docker network
- the bot does not reserve any host port
- the health API process itself stays internal and is exposed only through the reverse proxy when the `health` profile is enabled
- the current production Compose entrypoint is the `nginx` service, which binds `${NGINX_BIND_HOST:-127.0.0.1}:${NGINX_PORT:-8088}:80`
- public `80/443` are owned by the host Nginx on the shared server

Production services also use strict Docker log rotation limits to reduce disk growth on shared servers.

## HTTPS Observability Endpoint

Production observability is served through the shared host Nginx on:

- `https://monitoring.probochka-corp.ru/grafana/`
- `https://monitoring.probochka-corp.ru/health/`

The expected DNS record is:

```text
monitoring.probochka-corp.ru A 31.163.204.186
```

The runtime path is:

```text
Internet -> host nginx :443 -> http://127.0.0.1:8088 -> compose nginx -> grafana/health
```

The TLS certificate is managed by Certbot on the host, not by the application container. Certificate files must stay on the server under `/etc/letsencrypt` and must never be copied into the repository, logs, fixtures, Docker images, or GitHub Secrets.

The Compose Nginx is an internal HTTP upstream. It must not publish public `80/443` on a shared host.

The deployed production `.env` should include:

```env
PUBLIC_DOMAIN=monitoring.probochka-corp.ru
NGINX_BIND_HOST=127.0.0.1
NGINX_PORT=8088
HEALTH_API_ENABLED=true
```

Create the Certbot webroot on the server:

```bash
sudo mkdir -p /var/www/certbot
```

Install the host Nginx site for `monitoring.probochka-corp.ru`. If the certificate does not exist yet, enable only the `listen 80` server block first, run `sudo nginx -t`, and reload host Nginx.

```nginx
server {
    listen 80;
    server_name monitoring.probochka-corp.ru;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name monitoring.probochka-corp.ru;

    ssl_certificate /etc/letsencrypt/live/monitoring.probochka-corp.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/monitoring.probochka-corp.ru/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

Issue or refresh the certificate through the host Nginx webroot. Do not use `--standalone` on this shared host because host Nginx already owns port `80`.

```bash
sudo certbot certonly --webroot \
  -w /var/www/certbot \
  -d monitoring.probochka-corp.ru \
  --cert-name monitoring.probochka-corp.ru
sudo systemctl enable --now certbot.timer
sudo certbot renew --dry-run
```

After the certificate exists, enable the `listen 443 ssl` server block, then validate and reload host Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Install a Certbot deploy hook so renewed certificates are picked up by host Nginx:

```bash
sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-pybot-nginx.sh >/dev/null <<'SH'
#!/bin/sh
set -eu
systemctl reload nginx
SH
sudo chmod 0755 /etc/letsencrypt/renewal-hooks/deploy/reload-pybot-nginx.sh
```

Post-deploy smoke checks:

```bash
sudo nginx -t
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml exec nginx nginx -t
curl -I http://127.0.0.1:8088/health/
curl -i http://127.0.0.1:8088/health/ready
curl -I http://127.0.0.1:8088/grafana/
curl -I http://monitoring.probochka-corp.ru/health/
curl -I https://monitoring.probochka-corp.ru/health/
curl -I https://monitoring.probochka-corp.ru/grafana/
```

Expected results: internal `127.0.0.1:8088` health returns `200` when `HEALTH_API_ENABLED=true`, internal `/health/ready` returns `200` once the service is ready, internal Grafana returns a successful response or redirect, public HTTP redirects to HTTPS, public `/health/` returns `200`, and public Grafana returns a successful response or redirect under `/grafana/`.

To inspect the certificate served by host Nginx:

```bash
echo | openssl s_client \
  -connect monitoring.probochka-corp.ru:443 \
  -servername monitoring.probochka-corp.ru 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

The SAN must contain `DNS:monitoring.probochka-corp.ru`.

## Safety for Shared Servers

The normal CD flow is intentionally non-root:

- it does not install packages during routine deploys
- it does not change system services during routine deploys
- it only writes inside the configured deploy path and uses Docker commands available to the deploy user

This separation is meant to reduce the risk of affecting unrelated projects hosted on the same server.

## Post-Deploy Smoke Check

The deploy role performs a lightweight smoke-check after `docker compose up -d`, grouped as a dedicated post-deploy block in the deploy role:

- verifies that the core process types (`bot`, `taskiq-worker`, `taskiq-scheduler`, `redis`) appear in `docker compose ps`;
- waits for Redis health to become `healthy` when a healthcheck exists;
- when `HEALTH_API_ENABLED=true`, asserts that the `health` service appears in `docker compose ps`;
- when `HEALTH_API_ENABLED=true`, calls `GET http://127.0.0.1:8088/health/ready` through the production Compose Nginx path and fails the deploy unless it reaches `200`.

This complements CI by validating the deployed runtime on the real server instead of rerunning the same test suite, and it adds a real readiness gate for the production health profile.

## Operator Release Runbook

Use this short runbook after a manual deploy, failed CD run, or AI-assisted problem-solving session. Run it from the deploy path on the server:

```bash
cd /home/ilya/pybot
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=80 bot taskiq-worker taskiq-scheduler health nginx grafana
docker compose -f docker-compose.prod.yml exec nginx nginx -t
curl -I http://127.0.0.1:8088/health/
curl -i http://127.0.0.1:8088/health/ready
curl -I http://127.0.0.1:8088/grafana/
```

A release is healthy when the core services are `Up`, Redis is `healthy`, `nginx -t` succeeds, `/health/` returns `200`, `/health/ready` returns `200`, and `/grafana/` returns a successful Grafana response or redirect.

For the public observability endpoint, verify the host Nginx layer separately:

```bash
sudo nginx -t
curl -Iv --connect-timeout 5 --max-time 15 --resolve monitoring.probochka-corp.ru:4443:127.0.0.1 https://monitoring.probochka-corp.ru:4443/health/
curl -Iv --connect-timeout 5 --max-time 15 --resolve monitoring.probochka-corp.ru:4443:127.0.0.1 https://monitoring.probochka-corp.ru:4443/grafana/
```

Treat the public endpoint as healthy when the certificate is issued for `monitoring.probochka-corp.ru`, `/health/` returns `200`, and `/grafana/` returns a Grafana response or redirect. A timeout from the server to `https://monitoring.probochka-corp.ru/...` can be a hairpin routing limitation; prefer the `--resolve ...:4443:127.0.0.1` checks from the host and an external browser or monitoring check for the real public path.

If a smoke-check fails, do not restart everything blindly. First identify the failing layer:

- Compose service missing or restarting: inspect `docker compose -f docker-compose.prod.yml logs --tail=200 <service>` and fix that service before checking Nginx.
- Internal `127.0.0.1:8088` health or Grafana fails: check `pybot-nginx`, `health`, and `grafana` containers and their logs.
- Internal checks pass but public checks fail: inspect host Nginx with `sudo nginx -T`, `sudo nginx -t`, and `/var/log/nginx/error.log`.
- Certificate warning: inspect the served certificate and confirm the SAN contains `DNS:monitoring.probochka-corp.ru`; then check browser cache only after server-side TLS is confirmed.
- CD smoke-check fails after a new image: prefer redeploying the previous known-good image tag or rerunning the last successful workflow after the root cause is fixed.

## Health profile

The `health` process type is profile-gated in both Compose files.

- local/manual Compose can enable it with `COMPOSE_PROFILES=health` or `docker compose --profile health ...`
- production deploy enables `--profile health` only when `HEALTH_API_ENABLED=true` is present in the deployed `.env`
- when the profile is disabled, plain `docker compose up -d` does not start `pybot-health`
- when the profile is enabled, the process entrypoint is `uvicorn src.pybot.presentation.web:app`

## Migrations

Migrations are executed by the dedicated `migrate` service, not by `bot` startup.

That service is attached to the `migration` profile, so:

- local/manual Compose runs it explicitly with `docker compose --profile migration run --rm migrate`;
- production deploy runs it explicitly via Ansible before `docker compose up -d`;
- a plain `docker compose up -d` or `docker compose up --build` does not start it.

## Seed

Seed data is handled by the dedicated `seed` service, not by `bot` startup.

- it is disabled by default;
- local/manual Compose runs it explicitly with `docker compose --profile seed run --rm seed`;
- production deploy runs it only when `RUN_SEED_ON_DEPLOY=true` is passed from GitHub Secrets into the deploy workflow;
- it is intended for first deploys or controlled reinitialization, not for every rollout.

## Recommended production `.env` baseline

At minimum, set:

- `BOT_TOKEN`
- `BOT_TOKEN_TEST`
- `BOT_MODE=prod`
- `ROLE_REQUEST_ADMIN_TG_ID`
- `DATABASE_URL=sqlite+aiosqlite:///./data/pybot_itacadem.db`
- `FSM_STORAGE_BACKEND=redis`
- `REDIS_URL=redis://redis:6379/0`
- `AUTO_SEED_DB=false`
- `LOG_LEVEL=INFO`
- `HEALTH_API_ENABLED=true`
- `TASKIQ_WORKERS=1`
- `PUBLIC_DOMAIN=monitoring.probochka-corp.ru`
- `NGINX_BIND_HOST=127.0.0.1`
- `NGINX_PORT=8088`
- `LEADERBOARD_WEEKLY_RETRY_ENABLED=true`
- `LEADERBOARD_WEEKLY_RETRY_MAX_RETRIES=3`
- `LEADERBOARD_WEEKLY_RETRY_DELAY_S=30`
- `LEADERBOARD_WEEKLY_RETRY_USE_JITTER=true`
- `LEADERBOARD_WEEKLY_RETRY_USE_EXPONENTIAL_BACKOFF=true`
- `LEADERBOARD_WEEKLY_RETRY_MAX_DELAY_S=300`

Important:

- if you use SQLite in production, keep `DATABASE_URL` under `./data/...`
- paths like `sqlite+aiosqlite:///./pybot_itacadem.db` will place the database outside the mounted volume and break one-shot migration/seed containers
- when `HEALTH_API_ENABLED=true`, deploy orchestration enables the `health` Compose profile and starts a dedicated `pybot-health` service (`uvicorn src.pybot.presentation.web:app`)
- production uses the same concurrency knob as local Compose: `TASKIQ_WORKERS=1 docker compose up -d`
- syntax for future worker scaling is already reserved via `TASKIQ_WORKERS`, but values greater than `1` are intentionally rejected for now
- weekly leaderboard retries are applied only for temporary delivery failures (`NotificationTemporaryError`)
- retry policy for weekly publishing is controlled by `LEADERBOARD_WEEKLY_RETRY_*` env settings

## Next hardening steps

- Add a rollback workflow that redeploys a previous image tag
- Add external monitoring/log shipping
- Add image vulnerability scanning before deploy
