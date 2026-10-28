"""Single-origin, fail-closed production factory: verified static Pathline/MF + FastAPI.

The gateway key is added only inside the server, never sent to the browser.
Deploy only behind an HTTPS reverse proxy with correct forwarded headers.
"""
import os
import subprocess
import sys
from pathlib import Path
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from .app import create_app as create_backend

ROOT = Path(__file__).resolve().parents[1]

def create_app():
    if os.environ.get("GMF_ENV") != "production" or os.environ.get("GMF_AUTH_MODE") != "password":
        raise RuntimeError("Public site requires production/password mode")
    origin = os.environ.get("GMF_PUBLIC_ORIGIN", "")
    key = os.environ.get("GMF_GATEWAY_KEY", "")
    if not origin.startswith("https://") or len(key) < 32:
        raise RuntimeError("Public HTTPS origin and 32+ character gateway key required")
    data = Path(os.environ.get("GMF_DATA_DIR", "/var/data/gmf")).resolve()
    db = data / "modules.sqlite3"
    minimum = int(os.environ.get("GMF_MIN_PUBLISHED", "369"))
    if minimum < 369:
        raise RuntimeError("Production requires at least 369 reviewed questions; cannot lower gate")
    commands = [
        [sys.executable, str(ROOT / "scripts/verify-v43-deploy.py"),
         "--dist", str(ROOT / "dist"), "--mode", "assets-only"],
        [sys.executable, str(ROOT / "scripts/verify-public-bank.py"),
         "--db", str(db), "--data-root", str(data), "--min-published", str(minimum)],
    ]
    for cmd in commands:
        check = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        if check.returncode:
            raise RuntimeError("Public deployment preflight failed; refusing to serve empty site: "
                               + (check.stdout + check.stderr)[-3500:])
    app = create_backend(root=data)
    @app.middleware("http")
    async def same_origin_gateway(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            # Remove any browser-supplied gateway value; use server-side secret.
            headers = [(k, v) for k, v in request.scope["headers"] if k.lower() != b"x-gmf-gateway-key"]
            headers.append((b"x-gmf-gateway-key", key.encode("ascii")))
            request.scope["headers"] = headers
        return await call_next(request)
    app.mount("/", StaticFiles(directory=str(ROOT / "dist"), html=True), name="public-fusion")
    return app
