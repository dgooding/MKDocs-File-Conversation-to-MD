# One-click style deploy on Render

1. Push this repository to GitHub (public is fine).
2. Go to https://dashboard.render.com/select-repo?type=blueprint  
3. Connect `dgooding/MKDocs-File-Conversation-to-MD` (or your fork).
4. Apply the blueprint from `render.yaml`.
5. Wait for the Docker build (includes Tesseract + MarkItDown).
6. Open `https://<service>.onrender.com/convert/`

Health check path is already set to `/api/health`.
