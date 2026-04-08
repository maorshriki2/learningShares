# Local Nitter-compatible instance (Docker)

This folder contains a minimal Docker Compose setup to run a local Nitter instance on `http://127.0.0.1:8080`.

## Requirements

- Docker Desktop (Windows)
- A burner X/Twitter account (no 2FA)
- A `sessions.jsonl` file generated from that account (not committed; ignored by `.gitignore`)

## Run

From repo root:

```powershell
cd tools\nitter-local
docker compose up -d
```

## Test

Open:

- `http://127.0.0.1:8080/unusual_whales`

## Create `sessions.jsonl` (cookie method)

Nitter expects JSONL (one JSON object per line). The minimal shape is:

```json
{"kind":"cookie","auth_token":"...","ct0":"...","username":"...","id":0}
```

How to get `auth_token` and `ct0`:

- Log in to `x.com` with your burner account in Chrome/Edge.
- Open DevTools → Application → Cookies → `https://x.com`
- Copy the cookie values for `auth_token` and `ct0`.
- Replace the `REPLACE_ME` placeholders in `sessions.jsonl`.

Then restart the container:

```powershell
docker restart nitter
```

## Wire the app

Add to your `.env` (project root):

```env
NITTER_INSTANCES=http://127.0.0.1:8080
```

Then restart the app.

