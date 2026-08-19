from pathlib import Path

from fastapi.testclient import TestClient

from docs_to_markdown.api import app


ROOT = Path(__file__).parents[1]


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dockerfile_uses_locked_rootless_runtime() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim-bookworm AS builder" in dockerfile
    assert "uv sync --frozen --no-dev --no-editable" in dockerfile
    assert 'EXPOSE 8080' in dockerfile
    assert 'USER 1001' in dockerfile
    assert 'chmod -R g=u /app' in dockerfile
    assert '"--host", "0.0.0.0", "--port", "8080"' in dockerfile
    assert "http://127.0.0.1:8080/health" in dockerfile
    assert "tesseract" not in dockerfile.lower()


def test_docker_context_excludes_local_and_review_artifacts() -> None:
    ignored = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())

    assert {".marker-spike/", ".tools/", ".venv/", "review/", "site/", "tests/"} <= ignored


def test_openshift_manifest_uses_health_and_restricted_security() -> None:
    manifest = (ROOT / "deploy" / "openshift.yaml").read_text(encoding="utf-8")

    assert "containerPort: 8080" in manifest
    assert manifest.count("path: /health") == 2
    assert "allowPrivilegeEscalation: false" in manifest
    assert "readOnlyRootFilesystem: true" in manifest
    assert "runAsNonRoot: true" in manifest
    assert "type: RuntimeDefault" in manifest
    assert "mountPath: /tmp" in manifest
    assert "runAsUser:" not in manifest
