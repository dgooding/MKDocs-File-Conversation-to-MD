# Container deployment

The image runs the existing FastAPI application on port 8080. DOCX, PDF, scanned-PDF fallback, and batch requests use the same authoritative conversion functions as the local app.

## Docker

```powershell
docker build -t docs-to-markdown:latest .
docker run --rm -p 8080:8080 docs-to-markdown:latest
```

Open `http://127.0.0.1:8080/` or check `http://127.0.0.1:8080/health`.

## OpenShift

Push the image to an accessible registry, apply the manifest, and set the deployment image:

```powershell
oc apply -f deploy/openshift.yaml
oc set image deployment/docs-to-markdown app=<registry>/docs-to-markdown:<tag>
oc rollout status deployment/docs-to-markdown
oc get route docs-to-markdown
```

The manifest supports OpenShift's arbitrary UID, drops Linux capabilities, disables privilege escalation, uses a read-only root filesystem, and mounts an ephemeral `/tmp` directory.

Tesseract remains optional. A derived image may install it for OCR; without it, born-digital conversions and scanned-page visual fallback continue to work.