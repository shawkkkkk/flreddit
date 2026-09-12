# Deployment

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
