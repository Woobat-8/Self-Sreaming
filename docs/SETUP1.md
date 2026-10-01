# Server setup (Phase 1)

Members install **only the Flutter app**. This document is for the Ubuntu host admin.

## Prerequisites

- Ubuntu 22.04 or 24.04
- Docker and Docker Compose
- A **stable** hostname (your domain or a Cloudflare-managed hostname). Do not use ephemeral `trycloudflare.com` URLs.
- A Cloudflare account if you use a named tunnel (recommended: no inbound 443)

## Directory layout on the host

```
/opt/media-service/          # clone or copy of this repo's server/ directory
/mnt/media/library/shared/videos/
/mnt/media/library/shared/images/
```

Copy web-ready files only for Phase 1:

- Video: `.mp4` (fast-start) or `.webm`
- Images: `.jpg` / `.jpeg`, `.png`, `.webp`

Unsupported types are indexed as skipped and **never** appear in the library API.

## Configure

```bash
cd /opt/media-service
cp .env.example .env
# edit .env — set JWT_SECRET, MEDIA_SIGNING_SECRET, PUBLIC_BASE_URL,
# BOOTSTRAP_ADMIN_PASSWORD, and LIBRARY_HOST_PATH=/mnt/media/library
```

`PUBLIC_BASE_URL` must be the same HTTPS origin clients will type or scan, for example `https://media.example.com`. Signed media URLs are minted with this prefix.

## Run the API and Caddy

```bash
export LIBRARY_HOST_PATH=/mnt/media/library
docker compose up -d api caddy
```

Caddy listens on host port **8080** and reverse-proxies to the API. Local check:

```bash
curl -s http://127.0.0.1:8080/api/v1/health
```

Create an admin user if you did not set bootstrap env vars (or to add another admin):

```bash
docker compose exec api python -m app.cli create-admin --username admin --password 'choose-a-strong-password'
```

Reset a password:

```bash
docker compose exec api python -m app.cli reset-password --username admin
```

## Cloudflare Tunnel (preferred remote access)

1. In Cloudflare Zero Trust, create a **named** tunnel.
2. Point a public hostname at `http://127.0.0.1:8080` on the Ubuntu box (the Caddy port).
3. Put the tunnel token in `.env` as `CLOUDFLARE_TUNNEL_TOKEN`.
4. Start the tunnel container:

```bash
docker compose --profile tunnel up -d
```

Alternatively install `cloudflared` on the host and run it with systemd instead of the Compose profile. Either way, clients only need `https://your-hostname`.

UFW: allow SSH. The tunnel does **not** require opening 443.

## Alternative: port-forward + Let’s Encrypt

Forward WAN 443 to Caddy, put a real certificate on Caddy, and keep `PUBLIC_BASE_URL` as `https://your.domain`. Use strong passwords, fail2ban, and rate limiting. Prefer the tunnel when you can.

## First media and scan

1. Copy a sample `.mp4` into `.../shared/videos/` and a `.jpg` into `.../shared/images/`.
2. Log in and trigger a scan:

```bash
TOKEN=$(curl -s http://127.0.0.1:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"your-password"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -s -X POST http://127.0.0.1:8080/api/v1/admin/scan \
  -H "Authorization: Bearer $TOKEN"

curl -s http://127.0.0.1:8080/api/v1/library \
  -H "Authorization: Bearer $TOKEN"
```

The library JSON includes signed `stream`, `download`, and `thumbnail` URLs. Open the `stream` URL (with its `token` query) in curl or a browser to play; use `Range: bytes=0-1023` to confirm seek:

```bash
curl -I -H 'Range: bytes=0-1023' "$STREAM_URL"
```

You should see `206 Partial Content`.

Onboarding QR payload (admin):

```bash
curl -s http://127.0.0.1:8080/api/v1/onboarding/qr \
  -H "Authorization: Bearer $TOKEN"
```

Encode `payload` (the public HTTPS URL) as a QR for household phones.

## Optional periodic scan

Set `SCAN_INTERVAL_SECONDS=86400` in `.env` for a daily rescan, or call `POST /api/v1/admin/scan` after dropping files.

## Local development (no Docker)

From `server/`:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt   # Windows: .venv\Scripts\pip
copy .env.example .env                       # then edit
.venv/bin/python -m app.cli create-admin --username admin --password adminpass
.venv/bin/uvicorn app.main:app --reload --port 8080
.venv/bin/pytest
```

Install ffmpeg on the host if you want video duration, thumbnails, and MP4 fast-start remux.

## Phase 1 exit criteria

You can log in, list **playable** media, stream a fast-start MP4 with seek, and download a file against the **public HTTPS URL**, with no extra client apps and no custom CA.
