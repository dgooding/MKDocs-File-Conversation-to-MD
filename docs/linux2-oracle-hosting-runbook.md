# Linux2 Oracle Cloud Hosting Runbook

How **Docs to Markdown** was deployed on Sean’s Oracle Cloud Ubuntu host (`linux2`), and how to operate, update, and troubleshoot it.

This is the public-hosting path. Local Windows testers still use [LAUNCH.bat](../LAUNCH.bat) on `http://127.0.0.1:8000/`. Do not mix the two.

**Privacy:** Sean’s name is recorded as the VM owner. Do **not** commit host IPs, account names, emails, SSH public keys, or other addresses. Use `<HOST_IP>` and `<SSH_USER>`; ask Sean for the current values.

---

## 1. What this is

| Item | Value |
|------|--------|
| App | Docs to Markdown (this repository) |
| Host nickname | `linux2` |
| Cloud | Oracle Cloud Infrastructure (OCI) compute |
| OS | Ubuntu 24.04.4 LTS, kernel `6.17.0-1020-oracle`, x86_64 |
| Public IPv4 | `<HOST_IP>` — ask Sean; never commit the real address |
| SSH user | `<SSH_USER>` |
| SSH | `ssh <SSH_USER>@<HOST_IP>` |
| App URL | http://<HOST_IP>:8000/ |
| Converter | http://<HOST_IP>:8000/converter |
| Health | http://<HOST_IP>:8000/health |
| Container | `docs-to-markdown` |
| Image | `docs-to-markdown:latest` |
| Published port | **TCP 8000** → container 8000 |
| Repo on host | `/home/<SSH_USER>/MKDocs-File-Conversation-to-MD` |

The library, themed converter, batch page, and APIs all share **one port**. There is no separate 8001.

---

## 2. Who does what

Sean provided the VM and handles cloud firewall / host admin. Daniel (and this runbook) operate inside the VM as a normal user with Docker.

| Person | Can do | Cannot do |
|--------|--------|-----------|
| **Sean** | VM access, add SSH public keys, open/close cloud firewall ports, host `sudo` | — |
| **Daniel** | SSH in, use Docker **without sudo**, clone the repo, build/run/stop the app container | `sudo`, change cloud firewall rules from the VM, install host packages |

Confirmed on first login:

- login user is in the **`docker`** group
- `docker ps` works as `<SSH_USER>`
- `sudo docker ps` fails: *a terminal is required to read the password*

If a step needs `sudo` or an OCI console click, that is Sean’s job. Everything below that is Docker or files in `/home/<SSH_USER>` is Daniel’s job.

---

## 3. What we actually did (session log)

This is the real sequence from 2026-08-21, not a hypothetical.

1. **SSH key on the Windows PC**  
   Generated a local ed25519 key pair. **Never send the private key.** Only the `.pub` file was given to Sean.

2. **Sean installed that public key** on `linux2` in `/home/<SSH_USER>/.ssh/authorized_keys`.

3. **First SSH test** from Windows:

   ```powershell
   ssh -i $env:USERPROFILE\.ssh\id_ed25519 <SSH_USER>@<HOST_IP>
   ```

   Result: `CONNECTED`, user `<SSH_USER>`, host `linux2`. Host key was added to `known_hosts`.

4. **Inspected the box**  
   Docker Engine 29.7.2, Compose v5.5.0, Buildx v0.36.1.  
   Disk `/` 45 GB, ~36 GB free.  
   RAM **954 MiB**, **no swap**.  
   Host firewall was not visible to this user; the real gate is the cloud security list / NSG.  
   Only public listener at that moment: **TCP 22**.

5. **Asked Sean to open TCP 8000** on the cloud security list / NSG (ingress). Optional extras for a reverse proxy later: 80 and 443. SSH 22 was already open.

6. **Cloned this repo onto the box:**

   ```bash
   git clone <REPO_URL> ~/MKDocs-File-Conversation-to-MD
   ```

   Landed at commit `fb9f8a8` (*Publish IT service desk sample library*), branch `main`.

7. **The GitHub tree had no Dockerfile.** A production Dockerfile and `.dockerignore` were written and copied to the box (contents in [§6](#6-dockerfile-used-on-linux2)).

8. **Built the image on the box** (~5 minutes):

   ```bash
   cd ~/MKDocs-File-Conversation-to-MD
   docker build -t docs-to-markdown:latest .
   ```

   Image id: `213c6c9ce615…`

9. **Ran the container:**

   ```bash
   docker run -d --name docs-to-markdown --restart unless-stopped -p 8000:8000 docs-to-markdown:latest
   ```

   First ~40 seconds were MkDocs site build during FastAPI startup (`Waiting for application startup`). Then:

   - `Uvicorn running on http://0.0.0.0:8000`
   - Docker health: **healthy**
   - `GET /health` → `{"status":"ok"}`

10. **Verified from outside the VM** that OCI had opened 8000: `http://<HOST_IP>:8000/health` returned HTTP 200.

11. **End-to-end functional test** against the live container (see [§9](#9-how-we-proved-it-works)).

---

## 4. Access from Windows (repeatable)

OpenSSH is already on this PC (`C:\WINDOWS\System32\OpenSSH\ssh.exe`).

### 4.1 One-time key (already done on Daniel’s PC)

```powershell
New-Item -ItemType Directory -Path "$env:USERPROFILE\.ssh" -Force
ssh-keygen -t ed25519 -C "docs-to-markdown" -f "$env:USERPROFILE\.ssh\id_ed25519" -N '""'
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub"
```

Send Sean **only** the `.pub` line. He appends it to `~/.ssh/authorized_keys` for `<SSH_USER>`.

Optional, so you do not pass `-i` every time:

```powershell
Get-Service ssh-agent | Set-Service -StartupType Manual
Start-Service ssh-agent
ssh-add "$env:USERPROFILE\.ssh\id_ed25519"
```

### 4.2 Login

```powershell
ssh -i $env:USERPROFILE\.ssh\id_ed25519 <SSH_USER>@<HOST_IP>
```

Or open a visible window:

```powershell
Start-Process wt -ArgumentList "ssh","-i","$env:USERPROFILE\.ssh\id_ed25519","<SSH_USER>@<HOST_IP>"
```

First connect accepts the host ED25519 key into `known_hosts`. After that, `BatchMode` works:

```powershell
ssh -o BatchMode=yes -i $env:USERPROFILE\.ssh\id_ed25519 <SSH_USER>@<HOST_IP> "whoami; hostname"
```

Expected: `<SSH_USER>` / `linux2`.

### 4.3 Copy a file to the box

```powershell
scp -i $env:USERPROFILE\.ssh\id_ed25519 .\Dockerfile <SSH_USER>@<HOST_IP>:~/MKDocs-File-Conversation-to-MD/
```

---

## 5. Ports Sean must keep open

The VM process can bind `0.0.0.0:8000` and still be unreachable from the internet if OCI blocks it. Ask Sean to set **Ingress** on the instance VCN **security list** or **network security group**.

| Direction | Protocol | Port | Source | Why |
|-----------|----------|------|--------|-----|
| Ingress | TCP | **22** | your IP, or `0.0.0.0/0` if already used | SSH (already working) |
| Ingress | TCP | **8000** | `0.0.0.0/0` or a tight IP allow-list | Docs to Markdown HTTP |
| Ingress | TCP | 80 | optional | HTTP via a reverse proxy later |
| Ingress | TCP | 443 | optional | HTTPS via a reverse proxy later |

Do **not** need 8001. Do **not** open Docker’s random high ports.

Copy-paste for Sean:

```text
Need ingress TCP 8000 on linux2
(source 0.0.0.0/0, or lock to tester IPs).
22 is already fine.
Optional later: 80 and 443 if we put it behind a reverse proxy.
```

On the VM, confirm the container is listening:

```bash
ss -tlnp | grep 8000
# LISTEN 0.0.0.0:8000 and [::]:8000
```

From a laptop that is not the VM:

```powershell
Invoke-WebRequest http://<HOST_IP>:8000/health -UseBasicParsing
```

If the container is healthy but this times out, the OCI NSG is still closed.

---

## 6. Dockerfile used on linux2

This repository originally had **no** `Dockerfile`. The image on linux2 was built from the files below, placed in the repo root on the box.

### `Dockerfile`

```dockerfile
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/app/.venv/bin:$PATH" \
    HOME=/tmp \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra site --no-install-project --no-editable

COPY src ./src
COPY mkdocs-site ./mkdocs-site
RUN uv sync --frozen --no-dev --extra site --no-editable

RUN useradd --create-home --uid 1001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "docs_to_markdown.api:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
```

Why these choices:

- **Python 3.12 slim** matches `requires-python = ">=3.12"`.
- **uv locked sync** (`--frozen`) matches `uv.lock`. `--extra site` installs MkDocs so the library can build at startup. `--no-dev` keeps pytest/httpx out of production.
- **`libgomp1`** is required by ONNX Runtime / RapidOCR.
- **`src` + `mkdocs-site`** must be siblings. `mkdocs_publish.py` resolves the site as `Path(__file__).parents[2] / "mkdocs-site"`.
- **Listen `0.0.0.0:8000`**, not `127.0.0.1`. Inside Docker, localhost is only the container.
- **Non-root UID 1001**.
- **Healthcheck** hits `/health`, which FastAPI exposes as `{"status":"ok"}`.
- **`--start-period=40s`** because startup runs `build_mkdocs_site()` and can take half a minute on this 1 GB box.

### `.dockerignore`

```gitignore
.git
.github
.venv
**/__pycache__
**/*.pyc
tests
docs
sample-docs
site
mkdocs-site/site
INSTALL_AND_LAUNCH.ps1
LAUNCH.bat
AGENTS.md
```

`sample-docs` stays out of the image (large binaries). The library content that *is* baked in comes from `mkdocs-site/docs/`. The built HTML is generated at container start into `mkdocs-site/site`.

---

## 7. Build on the box

```bash
cd ~/MKDocs-File-Conversation-to-MD
git pull --ff-only origin main
docker build -t docs-to-markdown:latest .
docker images docs-to-markdown
```

First build pulled `python:3.12-slim-bookworm` and `ghcr.io/astral-sh/uv:0.8.22`, then installed 67 locked packages (FastAPI, MarkItDown, pdfplumber, RapidOCR, OpenCV, MkDocs, …). Observed wall time: **about 5 minutes**.

The box has **no swap and ~1 GB RAM**. Do not run a second heavy build while the app is converting a large PDF. If the build is OOM-killed, ask Sean for more RAM or a small swap file (that needs `sudo`).

---

## 8. Run / stop / restart

### Start (first time, or after `docker rm`)

```bash
docker run -d \
  --name docs-to-markdown \
  --restart unless-stopped \
  -p 8000:8000 \
  docs-to-markdown:latest
```

`--restart unless-stopped` brings it back after a VM reboot unless you explicitly stopped it.

### Day-2 commands

```bash
docker ps --filter name=docs-to-markdown
docker logs -f --tail 100 docs-to-markdown
docker restart docs-to-markdown
docker stop docs-to-markdown
docker start docs-to-markdown
```

### Replace with a newly built image

```bash
cd ~/MKDocs-File-Conversation-to-MD
git pull --ff-only origin main
docker build -t docs-to-markdown:latest .
docker rm -f docs-to-markdown
docker run -d --name docs-to-markdown --restart unless-stopped -p 8000:8000 docs-to-markdown:latest
```

Wait until logs show `Application startup complete` and `docker ps` says `(healthy)` before testing.

Published Markdown/DOCX/PDF inside the **container** are lost on `docker rm` unless you add a volume. The Git clone on disk (`~/MKDocs-File-Conversation-to-MD/mkdocs-site`) is separate from the running container filesystem. To persist library uploads across rebuilds, run with a bind mount (not used on the first deploy):

```bash
docker run -d \
  --name docs-to-markdown \
  --restart unless-stopped \
  -p 8000:8000 \
  -v ~/MKDocs-File-Conversation-to-MD/mkdocs-site:/app/mkdocs-site \
  docs-to-markdown:latest
```

Only add that volume if you intend the container to write into the git working tree.

---

## 9. How we proved it works

All of the following passed against the live container on 2026-08-21.

| Check | Result |
|--------|--------|
| `docker ps` | Up, port `0.0.0.0:8000->8000/tcp`, health **healthy** |
| `GET /health` (on-box and public IP) | HTTP 200 `{"status":"ok"}` |
| `GET /` | HTTP 200 HTML (~5.8 KB) — MkDocs library home |
| `GET /converter` | HTTP 200 HTML (~7.0 KB) — themed converter |
| `GET /batch` | HTTP 200 HTML |
| `GET /app/converter` | HTTP 200 HTML — standalone converter |
| `POST /api/convert` PDF `CHG-2407_Security_update_request.pdf` | HTTP 200 in **9.1 s**, Markdown ~2.7M chars including extracted page images |
| `POST /api/convert` matching `.docx` | HTTP 200 in **1.2 s**, headings + tables present (`# IT Service Desk Case CHG-2407`) |
| `POST /api/render` | HTTP 200 HTML (`<h1>IT Service Desk Case CHG-2407</h1>…`) |
| `POST /api/convert` a `.txt` file | HTTP **415** `Only DOCX and PDF files are supported` |

On-box convert example:

```bash
PDF=~/MKDocs-File-Conversation-to-MD/sample-docs/it-service-desk/CHG-2407_Security_update_request.pdf
curl -sS -F "file=@$PDF" http://127.0.0.1:8000/api/convert | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['filename'], len(d['markdown']))"
```

Browser smoke: open http://<HOST_IP>:8000/converter, drop a `.docx` or `.pdf`, Convert, confirm Markdown appears.

---

## 10. URLs and routes

Same process, same port.

| URL | What you get |
|-----|----------------|
| http://<HOST_IP>:8000/ | Document library home |
| http://<HOST_IP>:8000/converter | Themed converter (upload / preview / publish) |
| http://<HOST_IP>:8000/app/converter | Legacy standalone converter |
| http://<HOST_IP>:8000/batch | Batch ZIP converter |
| http://<HOST_IP>:8000/health | Liveness JSON |
| http://<HOST_IP>:8000/api/convert | POST multipart `file` |
| http://<HOST_IP>:8000/api/render | POST JSON `{ "markdown": "..." }` |
| http://<HOST_IP>:8000/api/publish | POST publish into the MkDocs library |
| http://<HOST_IP>:8000/mkdocs/ | Built site mount |

---

## 11. Host limits and gotchas

- **~1 GB RAM, 0 swap.** The running app sat around 190 MiB after startup. A large PDF convert plus a docker build at the same time can OOM the VM.
- **Startup is slow.** Uvicorn logs `Waiting for application startup` until MkDocs finishes. Healthchecks and `curl` during that window see connection reset. Wait for `Application startup complete`.
- **No sudo.** You cannot `apt install`, enable UFW, or add swap yourself. Ask Sean.
- **This is a public IP.** Anyone who can reach :8000 can convert files and, if they find publish, write into the container’s library. Treat it as a tester box, not a production secrets host. Do not upload real credentials or customer PII.
- **Corporate Windows proxy** (see `AGENTS.md`) does not apply on linux2. `uv` / Docker Hub / GitHub HTTPS from the VM worked without `--system-certs`.

---

## 12. Troubleshooting

### `Permission denied (publickey)`

Sean does not have your **current** `.pub` in `authorized_keys`, or you are using a different private key. Print the pub, send it again, SSH with `-i` pointing at the matching private key.

### SSH works, browser times out

Container not running, or OCI NSG missing TCP 8000.

```bash
docker ps --filter name=docs-to-markdown
ss -tlnp | grep 8000
curl -sS http://127.0.0.1:8000/health
```

If on-box curl works and public curl does not, it is the Oracle security list.

### Container restarts / unhealthy

```bash
docker logs --tail 200 docs-to-markdown
docker inspect --format '{{.State.Status}} {{.State.OOMKilled}} {{.State.Health.Status}}' docs-to-markdown
free -h
```

If `OOMKilled` is true, ask Sean for RAM or swap.

### `Only DOCX and PDF files are supported`

Expected for any other extension (HTTP 415).

### Conversion 422

Empty file, or the engine could not parse that document. Retry with a sample under `sample-docs/it-service-desk/`.

### Stale UI after a rebuild

Hard-refresh the browser. Confirm you hit `:8000` on the public IP, not an old local `LAUNCH.bat` on `127.0.0.1:8000`.

### Need to start over

```bash
docker rm -f docs-to-markdown
cd ~/MKDocs-File-Conversation-to-MD
docker build -t docs-to-markdown:latest .
docker run -d --name docs-to-markdown --restart unless-stopped -p 8000:8000 docs-to-markdown:latest
```

---

## 13. Security notes

- Share **public** keys only (`*.pub`). The file `id_ed25519` without `.pub` is the private key.
- Do not commit host IPs, emails, SSH keys, OCI API keys, or real uploaded documents to GitHub.
- Prefer locking NSG source IPs to testers instead of `0.0.0.0/0` once the app is no longer a wide demo.
- The `<SSH_USER>` account cannot sudo; that is intentional isolation on the shared VM.

---

## 14. Quick reference

```bash
# SSH
ssh <SSH_USER>@<HOST_IP>

# Status
docker ps --filter name=docs-to-markdown
curl -sS http://127.0.0.1:8000/health

# Logs
docker logs -f --tail 100 docs-to-markdown

# Rebuild and replace
cd ~/MKDocs-File-Conversation-to-MD
git pull --ff-only origin main
docker build -t docs-to-markdown:latest .
docker rm -f docs-to-markdown
docker run -d --name docs-to-markdown --restart unless-stopped -p 8000:8000 docs-to-markdown:latest
```

Public check from anywhere:

```text
http://<HOST_IP>:8000/health
http://<HOST_IP>:8000/converter
```
