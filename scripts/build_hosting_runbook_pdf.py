"""Build the Linux2 hosting runbook PDF. No host IPs, account names, or emails."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "docs" / "linux2-oracle-hosting-runbook.pdf"

NAVY = colors.HexColor("#1b365d")
RULE = colors.HexColor("#c5cdd6")
HEAD_BG = colors.HexColor("#e8eef4")
CODE_BG = colors.HexColor("#f4f6f8")
MUTED = colors.HexColor("#4a5560")


def styles():
    base = getSampleStyleSheet()
    s = {
        "cover": ParagraphStyle(
            "cover",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=22,
            leading=26,
            textColor=NAVY,
            spaceAfter=8,
            alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=11,
            leading=14,
            textColor=MUTED,
            spaceAfter=16,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=14,
            leading=18,
            textColor=NAVY,
            spaceBefore=16,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Times-Bold",
            fontSize=12,
            leading=15,
            textColor=NAVY,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=13,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=13,
            leftIndent=12,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8.5,
            leading=11,
        ),
        "cellh": ParagraphStyle(
            "cellh",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=8.5,
            leading=11,
            textColor=NAVY,
        ),
        "code": ParagraphStyle(
            "code",
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            backColor=CODE_BG,
            leftIndent=4,
            rightIndent=4,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "note": ParagraphStyle(
            "note",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=9,
            leading=12,
            textColor=MUTED,
            spaceAfter=10,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Times-Roman",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_LEFT,
        ),
    }
    return s


def P(text, style):
    return Paragraph(text, style)


def code_block(text, st):
    return Preformatted(text.strip("\n"), st["code"])


def table(headers, rows, st, col_widths):
    head = [P(f"<b>{h}</b>", st["cellh"]) for h in headers]
    body = [[P(c, st["cell"]) for c in row] for row in rows]
    t = Table([head] + body, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def bullets(items, st):
    return ListFlowable(
        [ListItem(P(item, st["bullet"]), leftIndent=12, bulletColor=NAVY) for item in items],
        bulletType="bullet",
        start="•",
        leftIndent=18,
        bulletFontName="Times-Roman",
        bulletFontSize=10,
    )


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(1.2)
    canvas.line(0.75 * inch, letter[1] - 0.5 * inch, letter[0] - 0.75 * inch, letter[1] - 0.5 * inch)
    canvas.setFont("Times-Italic", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.75 * inch, letter[1] - 0.42 * inch, "Docs to Markdown  —  Linux2 Oracle Cloud Hosting Runbook")
    canvas.line(0.75 * inch, 0.55 * inch, letter[0] - 0.75 * inch, 0.55 * inch)
    canvas.drawString(0.75 * inch, 0.38 * inch, "No host addresses, account names, or keys in this document.")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build():
    st = styles()
    story = []
    usable = 7.0 * inch

    story.append(P("Linux2 Oracle Cloud Hosting Runbook", st["cover"]))
    story.append(P("How Docs to Markdown was deployed on Sean’s Ubuntu host, and how to operate it.", st["subtitle"]))
    story.append(
        P(
            "This is the public-hosting path. Local Windows testers still use LAUNCH.bat on "
            "http://127.0.0.1:8000/. Do not mix the two.",
            st["body"],
        )
    )
    story.append(
        P(
            "<b>Privacy.</b> Sean is named as the VM owner. This PDF does not contain host IPs, "
            "SSH account names, emails, or public keys. Use the placeholders "
            "<font face='Courier'>&lt;HOST_IP&gt;</font>, "
            "<font face='Courier'>&lt;SSH_USER&gt;</font>, and "
            "<font face='Courier'>&lt;REPO_URL&gt;</font>. Ask Sean for the current values. "
            "Never commit those values to Git.",
            st["note"],
        )
    )

    story.append(P("1. What this is", st["h1"]))
    story.append(
        table(
            ["Item", "Value"],
            [
                ["App", "Docs to Markdown (this repository)"],
                ["Host nickname", "linux2"],
                ["Cloud", "Oracle Cloud Infrastructure (OCI) compute"],
                ["OS", "Ubuntu 24.04 LTS, x86_64"],
                ["Public IPv4", "&lt;HOST_IP&gt; — ask Sean; never publish the real address"],
                ["SSH user", "&lt;SSH_USER&gt;"],
                ["SSH", "ssh &lt;SSH_USER&gt;@&lt;HOST_IP&gt;"],
                ["App URL", "http://&lt;HOST_IP&gt;:8000/"],
                ["Converter", "http://&lt;HOST_IP&gt;:8000/converter"],
                ["Health", "http://&lt;HOST_IP&gt;:8000/health"],
                ["Container", "docs-to-markdown"],
                ["Image", "docs-to-markdown:latest"],
                ["Published port", "TCP 8000 → container 8000"],
                ["Repo on host", "~/MKDocs-File-Conversation-to-MD"],
            ],
            st,
            [1.7 * inch, 5.3 * inch],
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        P(
            "The library, themed converter, batch page, and APIs all share <b>one port</b>. "
            "There is no separate 8001.",
            st["body"],
        )
    )

    story.append(P("2. Who does what", st["h1"]))
    story.append(
        P(
            "Sean provided the VM and handles cloud firewall / host admin. Daniel operates "
            "inside the VM as a normal user with Docker.",
            st["body"],
        )
    )
    story.append(
        table(
            ["Person", "Can do", "Cannot do"],
            [
                [
                    "Sean",
                    "VM access, add SSH public keys, open/close cloud firewall ports, host sudo",
                    "—",
                ],
                [
                    "Daniel",
                    "SSH in, use Docker without sudo, clone the repo, build/run/stop the app container",
                    "sudo, change cloud firewall rules from the VM, install host packages",
                ],
            ],
            st,
            [1.1 * inch, 3.3 * inch, 2.6 * inch],
        )
    )
    story.append(Spacer(1, 8))
    story.append(P("Confirmed on first login:", st["body"]))
    story.append(
        bullets(
            [
                "Login user is in the <font face='Courier'>docker</font> group.",
                "<font face='Courier'>docker ps</font> works without sudo.",
                "sudo requires a password this account does not have.",
            ],
            st,
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        P(
            "If a step needs sudo or an OCI console click, that is Sean’s job. Everything "
            "that is Docker or files in the home directory is Daniel’s job.",
            st["body"],
        )
    )

    story.append(P("3. What we actually did", st["h1"]))
    story.append(P("Real sequence from 21 August 2026, not a hypothetical.", st["note"]))
    steps = [
        "<b>SSH key on the Windows PC.</b> Generated a local ed25519 key pair. Never send the private key. Only the .pub file was given to Sean.",
        "<b>Sean installed that public key</b> on linux2 in the login user’s authorized_keys file.",
        "<b>First SSH test</b> from Windows succeeded. Host key was added to known_hosts.",
        "<b>Inspected the box.</b> Docker Engine 29.x with Compose and Buildx. About 36 GB free disk. About 1 GB RAM and no swap. Host firewall was not visible to this user; the real gate is the cloud security list / NSG. Only TCP 22 was listening publicly at that moment.",
        "<b>Asked Sean to open TCP 8000</b> on the cloud security list / NSG (ingress). Optional later: 80 and 443 for a reverse proxy. SSH 22 was already open.",
        "<b>Cloned this repository</b> onto the box into ~/MKDocs-File-Conversation-to-MD (branch main).",
        "<b>The GitHub tree had no Dockerfile.</b> A production Dockerfile and .dockerignore were written and copied to the box (section 6).",
        "<b>Built the image on the box</b> (~5 minutes): docker build -t docs-to-markdown:latest .",
        "<b>Ran the container</b> with --restart unless-stopped and -p 8000:8000. First ~40 seconds were MkDocs site build during FastAPI startup. Then Uvicorn listened on 0.0.0.0:8000, Docker health was healthy, and GET /health returned {\"status\":\"ok\"}.",
        "<b>Verified from outside the VM</b> that TCP 8000 was open: public GET /health returned HTTP 200.",
        "<b>End-to-end functional test</b> against the live container (section 9).",
    ]
    for i, step in enumerate(steps, 1):
        story.append(P(f"{i}. {step}", st["body"]))

    story.append(P("4. Access from Windows (repeatable)", st["h1"]))
    story.append(P("OpenSSH is already on the PC (Windows OpenSSH).", st["body"]))
    story.append(P("4.1 One-time key", st["h2"]))
    story.append(
        code_block(
            """New-Item -ItemType Directory -Path "$env:USERPROFILE\\.ssh" -Force
ssh-keygen -t ed25519 -C "docs-to-markdown" -f "$env:USERPROFILE\\.ssh\\id_ed25519" -N '""'
Get-Content "$env:USERPROFILE\\.ssh\\id_ed25519.pub" """,
            st,
        )
    )
    story.append(
        P(
            "Send Sean <b>only</b> the .pub line. He appends it to authorized_keys for &lt;SSH_USER&gt;.",
            st["body"],
        )
    )
    story.append(P("Optional, so you do not pass -i every time:", st["body"]))
    story.append(
        code_block(
            """Get-Service ssh-agent | Set-Service -StartupType Manual
Start-Service ssh-agent
ssh-add "$env:USERPROFILE\\.ssh\\id_ed25519" """,
            st,
        )
    )
    story.append(P("4.2 Login", st["h2"]))
    story.append(
        code_block(
            'ssh -i $env:USERPROFILE\\.ssh\\id_ed25519 <SSH_USER>@<HOST_IP>',
            st,
        )
    )
    story.append(P("Or open a visible window:", st["body"]))
    story.append(
        code_block(
            'Start-Process wt -ArgumentList "ssh","-i","$env:USERPROFILE\\.ssh\\id_ed25519","<SSH_USER>@<HOST_IP>"',
            st,
        )
    )
    story.append(P("BatchMode after the host key is known:", st["body"]))
    story.append(
        code_block(
            'ssh -o BatchMode=yes -i $env:USERPROFILE\\.ssh\\id_ed25519 <SSH_USER>@<HOST_IP> "whoami; hostname"',
            st,
        )
    )
    story.append(P("Expected: &lt;SSH_USER&gt; / linux2.", st["body"]))
    story.append(P("4.3 Copy a file to the box", st["h2"]))
    story.append(
        code_block(
            "scp -i $env:USERPROFILE\\.ssh\\id_ed25519 .\\Dockerfile <SSH_USER>@<HOST_IP>:~/MKDocs-File-Conversation-to-MD/",
            st,
        )
    )

    story.append(P("5. Ports Sean must keep open", st["h1"]))
    story.append(
        P(
            "The VM can bind 0.0.0.0:8000 and still be unreachable if OCI blocks it. Ask Sean "
            "to set Ingress on the instance VCN security list or network security group.",
            st["body"],
        )
    )
    story.append(
        table(
            ["Direction", "Protocol", "Port", "Source", "Why"],
            [
                ["Ingress", "TCP", "22", "tester IPs, or 0.0.0.0/0 if already used", "SSH (already working)"],
                ["Ingress", "TCP", "8000", "0.0.0.0/0 or a tight allow-list", "Docs to Markdown HTTP"],
                ["Ingress", "TCP", "80", "optional", "HTTP via a reverse proxy later"],
                ["Ingress", "TCP", "443", "optional", "HTTPS via a reverse proxy later"],
            ],
            st,
            [1.05 * inch, 0.85 * inch, 0.7 * inch, 2.2 * inch, 2.2 * inch],
        )
    )
    story.append(Spacer(1, 8))
    story.append(P("Do not need 8001. Do not open Docker’s random high ports.", st["body"]))
    story.append(P("Copy-paste for Sean:", st["body"]))
    story.append(
        code_block(
            """Need ingress TCP 8000 on linux2
(source 0.0.0.0/0, or lock to tester IPs).
22 is already fine.
Optional later: 80 and 443 if we put it behind a reverse proxy.""",
            st,
        )
    )
    story.append(P("On the VM, confirm the container is listening:", st["body"]))
    story.append(code_block("ss -tlnp | grep 8000", st))
    story.append(P("From a laptop that is not the VM:", st["body"]))
    story.append(
        code_block(
            "Invoke-WebRequest http://<HOST_IP>:8000/health -UseBasicParsing",
            st,
        )
    )
    story.append(
        P(
            "If the container is healthy but this times out, the OCI NSG is still closed.",
            st["body"],
        )
    )

    story.append(P("6. Dockerfile used on linux2", st["h1"]))
    story.append(
        P(
            "This repository originally had no Dockerfile. The image on linux2 was built from "
            "the files below, placed in the repo root on the box.",
            st["body"],
        )
    )
    story.append(P("Dockerfile", st["h2"]))
    story.append(
        code_block(
            """FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv

RUN apt-get update \\
    && apt-get install -y --no-install-recommends libgomp1 \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \\
    UV_LINK_MODE=copy \\
    UV_PYTHON_DOWNLOADS=0 \\
    PATH="/app/.venv/bin:$PATH" \\
    HOME=/tmp \\
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra site --no-install-project --no-editable

COPY src ./src
COPY mkdocs-site ./mkdocs-site
RUN uv sync --frozen --no-dev --extra site --no-editable

RUN useradd --create-home --uid 1001 appuser \\
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "docs_to_markdown.api:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]""",
            st,
        )
    )
    story.append(P("Why these choices:", st["body"]))
    story.append(
        bullets(
            [
                "<b>Python 3.12 slim</b> matches requires-python &gt;= 3.12.",
                "<b>uv locked sync</b> (--frozen) matches uv.lock. --extra site installs MkDocs so the library can build at startup. --no-dev keeps pytest out of production.",
                "<b>libgomp1</b> is required by ONNX Runtime / RapidOCR.",
                "<b>src + mkdocs-site</b> must be siblings. mkdocs_publish.py resolves the site as two parents up from the package, then / mkdocs-site.",
                "<b>Listen 0.0.0.0:8000</b>, not 127.0.0.1. Inside Docker, localhost is only the container.",
                "<b>Non-root UID 1001.</b>",
                "<b>Healthcheck</b> hits /health, which returns {\"status\":\"ok\"}.",
                "<b>start-period 40s</b> because startup runs build_mkdocs_site() and can take half a minute on this 1 GB box.",
            ],
            st,
        )
    )
    story.append(P(".dockerignore", st["h2"]))
    story.append(
        code_block(
            """.git
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
AGENTS.md""",
            st,
        )
    )
    story.append(
        P(
            "sample-docs stays out of the image. Library content that is baked in comes from "
            "mkdocs-site/docs/. Built HTML is generated at container start into mkdocs-site/site.",
            st["body"],
        )
    )

    story.append(P("7. Build on the box", st["h1"]))
    story.append(
        code_block(
            """cd ~/MKDocs-File-Conversation-to-MD
git pull --ff-only origin main
docker build -t docs-to-markdown:latest .
docker images docs-to-markdown""",
            st,
        )
    )
    story.append(
        P(
            "First build pulled python:3.12-slim-bookworm and the official uv image, then "
            "installed 67 locked packages (FastAPI, MarkItDown, pdfplumber, RapidOCR, OpenCV, "
            "MkDocs, …). Observed wall time: about 5 minutes.",
            st["body"],
        )
    )
    story.append(
        P(
            "The box has no swap and about 1 GB RAM. Do not run a second heavy build while the "
            "app is converting a large PDF. If the build is OOM-killed, ask Sean for more RAM "
            "or a small swap file (that needs sudo).",
            st["body"],
        )
    )

    story.append(P("8. Run / stop / restart", st["h1"]))
    story.append(P("Start (first time, or after docker rm)", st["h2"]))
    story.append(
        code_block(
            """docker run -d \\
  --name docs-to-markdown \\
  --restart unless-stopped \\
  -p 8000:8000 \\
  docs-to-markdown:latest""",
            st,
        )
    )
    story.append(
        P(
            "--restart unless-stopped brings it back after a VM reboot unless you explicitly stopped it.",
            st["body"],
        )
    )
    story.append(P("Day-2 commands", st["h2"]))
    story.append(
        code_block(
            """docker ps --filter name=docs-to-markdown
docker logs -f --tail 100 docs-to-markdown
docker restart docs-to-markdown
docker stop docs-to-markdown
docker start docs-to-markdown""",
            st,
        )
    )
    story.append(P("Replace with a newly built image", st["h2"]))
    story.append(
        code_block(
            """cd ~/MKDocs-File-Conversation-to-MD
git pull --ff-only origin main
docker build -t docs-to-markdown:latest .
docker rm -f docs-to-markdown
docker run -d --name docs-to-markdown --restart unless-stopped -p 8000:8000 docs-to-markdown:latest""",
            st,
        )
    )
    story.append(
        P(
            "Wait until logs show Application startup complete and docker ps says (healthy) before testing.",
            st["body"],
        )
    )
    story.append(
        P(
            "Published files inside the container are lost on docker rm unless you add a volume. "
            "The Git clone on disk is separate from the running container filesystem. To persist "
            "library uploads across rebuilds (not used on the first deploy):",
            st["body"],
        )
    )
    story.append(
        code_block(
            """docker run -d \\
  --name docs-to-markdown \\
  --restart unless-stopped \\
  -p 8000:8000 \\
  -v ~/MKDocs-File-Conversation-to-MD/mkdocs-site:/app/mkdocs-site \\
  docs-to-markdown:latest""",
            st,
        )
    )
    story.append(
        P(
            "Only add that volume if you intend the container to write into the git working tree.",
            st["body"],
        )
    )

    story.append(P("9. How we proved it works", st["h1"]))
    story.append(P("All of the following passed against the live container on 21 August 2026.", st["note"]))
    story.append(
        table(
            ["Check", "Result"],
            [
                ["docker ps", "Up, port 0.0.0.0:8000→8000/tcp, health healthy"],
                ["GET /health (on-box and public)", "HTTP 200 {\"status\":\"ok\"}"],
                ["GET /", "HTTP 200 HTML — MkDocs library home"],
                ["GET /converter", "HTTP 200 HTML — themed converter"],
                ["GET /batch", "HTTP 200 HTML"],
                ["GET /app/converter", "HTTP 200 HTML — standalone converter"],
                ["POST /api/convert sample PDF", "HTTP 200 in 9.1 s, Markdown with extracted page images"],
                ["POST /api/convert matching DOCX", "HTTP 200 in 1.2 s, headings and tables present"],
                ["POST /api/render", "HTTP 200 HTML preview"],
                ["POST /api/convert a .txt file", "HTTP 415 Only DOCX and PDF files are supported"],
            ],
            st,
            [2.4 * inch, 4.6 * inch],
        )
    )
    story.append(Spacer(1, 8))
    story.append(P("On-box convert example:", st["body"]))
    story.append(
        code_block(
            """PDF=~/MKDocs-File-Conversation-to-MD/sample-docs/it-service-desk/<sample>.pdf
curl -sS -F "file=@$PDF" http://127.0.0.1:8000/api/convert""",
            st,
        )
    )
    story.append(
        P(
            "Browser smoke: open http://&lt;HOST_IP&gt;:8000/converter, drop a .docx or .pdf, Convert, confirm Markdown appears.",
            st["body"],
        )
    )

    story.append(P("10. URLs and routes", st["h1"]))
    story.append(P("Same process, same port. Replace &lt;HOST_IP&gt; with the value Sean gives you.", st["body"]))
    story.append(
        table(
            ["URL", "What you get"],
            [
                ["http://&lt;HOST_IP&gt;:8000/", "Document library home"],
                ["http://&lt;HOST_IP&gt;:8000/converter", "Themed converter (upload / preview / publish)"],
                ["http://&lt;HOST_IP&gt;:8000/app/converter", "Legacy standalone converter"],
                ["http://&lt;HOST_IP&gt;:8000/batch", "Batch ZIP converter"],
                ["http://&lt;HOST_IP&gt;:8000/health", "Liveness JSON"],
                ["http://&lt;HOST_IP&gt;:8000/api/convert", "POST multipart file"],
                ["http://&lt;HOST_IP&gt;:8000/api/render", "POST JSON markdown preview"],
                ["http://&lt;HOST_IP&gt;:8000/api/publish", "POST publish into the MkDocs library"],
                ["http://&lt;HOST_IP&gt;:8000/mkdocs/", "Built site mount"],
            ],
            st,
            [3.2 * inch, 3.8 * inch],
        )
    )

    story.append(P("11. Host limits and gotchas", st["h1"]))
    story.append(
        bullets(
            [
                "<b>~1 GB RAM, 0 swap.</b> The running app sat around 190 MiB after startup. A large PDF convert plus a docker build at the same time can OOM the VM.",
                "<b>Startup is slow.</b> Uvicorn logs Waiting for application startup until MkDocs finishes. curl during that window can see connection reset. Wait for Application startup complete.",
                "<b>No sudo.</b> You cannot apt install, enable UFW, or add swap yourself. Ask Sean.",
                "<b>Public service.</b> Anyone who can reach :8000 can convert files and, if they find publish, write into the container’s library. Treat it as a tester box. Do not upload credentials or customer PII.",
                "The corporate Windows proxy described in AGENTS.md does not apply on linux2. uv / Docker Hub / GitHub HTTPS from the VM worked without extra cert flags.",
            ],
            st,
        )
    )

    story.append(P("12. Troubleshooting", st["h1"]))
    story.append(P("Permission denied (publickey)", st["h2"]))
    story.append(
        P(
            "Sean does not have your current .pub in authorized_keys, or you are using a different "
            "private key. Print the pub, send it again, SSH with -i pointing at the matching private key.",
            st["body"],
        )
    )
    story.append(P("SSH works, browser times out", st["h2"]))
    story.append(P("Container not running, or OCI NSG missing TCP 8000.", st["body"]))
    story.append(
        code_block(
            """docker ps --filter name=docs-to-markdown
ss -tlnp | grep 8000
curl -sS http://127.0.0.1:8000/health""",
            st,
        )
    )
    story.append(
        P(
            "If on-box curl works and public curl does not, it is the Oracle security list.",
            st["body"],
        )
    )
    story.append(P("Container restarts / unhealthy", st["h2"]))
    story.append(
        code_block(
            """docker logs --tail 200 docs-to-markdown
docker inspect docs-to-markdown
free -h""",
            st,
        )
    )
    story.append(P("If OOMKilled is true, ask Sean for RAM or swap.", st["body"]))
    story.append(P("Only DOCX and PDF files are supported", st["h2"]))
    story.append(P("Expected for any other extension (HTTP 415).", st["body"]))
    story.append(P("Conversion 422", st["h2"]))
    story.append(
        P(
            "Empty file, or the engine could not parse that document. Retry with a sample under sample-docs/.",
            st["body"],
        )
    )
    story.append(P("Stale UI after a rebuild", st["h2"]))
    story.append(
        P(
            "Hard-refresh the browser. Confirm you hit :8000 on the host, not an old local LAUNCH.bat on 127.0.0.1:8000.",
            st["body"],
        )
    )
    story.append(P("Need to start over", st["h2"]))
    story.append(
        code_block(
            """docker rm -f docs-to-markdown
cd ~/MKDocs-File-Conversation-to-MD
docker build -t docs-to-markdown:latest .
docker run -d --name docs-to-markdown --restart unless-stopped -p 8000:8000 docs-to-markdown:latest""",
            st,
        )
    )

    story.append(P("13. Security notes", st["h1"]))
    story.append(
        bullets(
            [
                "Share public keys only (*.pub). The file id_ed25519 without .pub is the private key.",
                "Do not commit host IPs, account names, emails, SSH keys, OCI API keys, or real uploaded documents to Git.",
                "Prefer locking NSG source IPs to testers instead of 0.0.0.0/0 once the app is no longer a wide demo.",
                "The login account cannot sudo; that is intentional isolation on the shared VM.",
            ],
            st,
        )
    )

    story.append(P("14. Quick reference", st["h1"]))
    story.append(
        code_block(
            """# SSH
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

# Public check
http://<HOST_IP>:8000/health
http://<HOST_IP>:8000/converter""",
            st,
        )
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="Linux2 Oracle Cloud Hosting Runbook",
        author="Docs to Markdown",
        subject="Hosting runbook with no host addresses or account names",
    )
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(OUT)


if __name__ == "__main__":
    build()
