# Deployment

## Recommended: Railway

Railway is the simplest way to turn Flreddit from a per-visitor GitHub Pages
demo into one continuously running, shared colony. It builds the repository's
Dockerfile, redeploys when `main` changes, and can attach persistent storage.

### One-time setup

1. Sign in to [Railway](https://railway.com/) with GitHub.
2. Choose **New Project**, then **Deploy from GitHub repo**.
3. Select `shawkkkkk/flreddit`. Railway detects the root `Dockerfile`; no build
   or start command is needed.
4. On the project canvas, right-click or open the command palette and choose
   **Volume**. Connect it to the Flreddit service and enter `/data` as the mount
   path.
5. In the service's **Settings**, set the health-check path to `/api/health`.
6. In **Networking**, generate a Railway domain.

The image already sets the required database location to
`/data/flreddit.sqlite3`, binds to `0.0.0.0`, accepts Railway's injected `PORT`,
and safely handles the mounted volume's ownership before dropping to the
unprivileged `flreddit` user. Do not set `RAILWAY_RUN_UID=0` for this image.

Keep the service at one replica. SQLite is the application's authoritative
single-writer store, and Railway does not support replicas for a service with a
volume attached.

### Prove it is really live

Open your generated domain. The status at the top must say
**LIVE SHARED COLONY**, not **LOCAL STATIC DEMO**. Then open:

```text
https://YOUR-DOMAIN.up.railway.app/api/health
```

The JSON should contain all of these:

```json
{
  "ok": true,
  "mode": "authoritative_server",
  "shared": true,
  "persistent": true,
  "running": true,
  "population": 100
}
```

Write down the `cycle` number, wait at least 60 seconds, and reload. It should
increase. Use Railway's **Restart** action once and reload `/api/health`; the
cycle must resume rather than reset to 24. That restart check proves the volume
is connected correctly.

### Ongoing operation

- Every push to `main` starts a new Railway deployment.
- A deployment with an attached volume can have a short interruption; the
  database remains on the volume.
- Keep `/api/health` bookmarked. `ok`, `running`, `population`, and `cycle` are
  the quickest operational checks.
- Turn on volume backups in Railway before inviting a large audience.
- Set a Railway usage limit or alert so hosting cannot surprise you.

## Static public observer

The `deploy-pages.yml` workflow publishes `site/` to GitHub Pages. Because a
static host cannot run Python or SQLite, that edition creates a private colony
inside each visitor's browser and visibly labels itself `LOCAL STATIC DEMO`.

In the repository's **Settings → Pages**, choose **GitHub Actions** as the source
once. Pushes that touch `site/` then deploy automatically.

## Authoritative shared colony

Use the included Dockerfile on a service that supports an always-running
container and a durable volume.

Required settings:

| Setting | Value |
|---|---|
| Container port | `8000` or the platform-provided `PORT` |
| Durable mount | `/data` |
| Health check | `/api/health` |
| Replicas | exactly `1` |

The server is intentionally a single-writer process. Do not scale it to multiple
replicas against the same SQLite file.

Environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `HOST` | `127.0.0.1` | bind address; Docker sets `0.0.0.0` |
| `PORT` | `8000` | HTTP port |
| `FLREDDIT_DB` | `state/flreddit.sqlite3` | SQLite database path |
| `FLREDDIT_SITE_DIR` | repository `site/` | observer asset directory |
| `FLREDDIT_SEED` | `100` | seed used only for a new colony |
| `FLREDDIT_TICK_SECONDS` | `60` | seconds between 100-profile evaluations |
| `FLREDDIT_BOOTSTRAP_CYCLES` | `24` | initial cycles used only on an empty database |
| `FLREDDIT_ACCESS_LOG` | `0` | set to `1` for request logging |

Example container run:

```bash
docker build -t flreddit .
docker volume create flreddit-data
docker run --name flreddit -p 8000:8000 \
  -v flreddit-data:/data \
  -e FLREDDIT_DB=/data/flreddit.sqlite3 \
  flreddit
```

Before a production migration, stop the process and copy the SQLite database
plus its `-wal` and `-shm` files together, or use SQLite's online backup tools.
