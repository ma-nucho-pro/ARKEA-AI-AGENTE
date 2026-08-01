import os
import sys
import secrets
from pathlib import Path

if getattr(sys, "frozen", False):
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    bundle_dir = Path(__file__).resolve().parent

os.environ.setdefault("ARKEA_BUNDLE_DIR", str(bundle_dir))
host = os.getenv("ARKEA_HOST", "127.0.0.1")
dev_no_auth = os.getenv("ARKEA_DEV_NO_AUTH", "") == "1"
if dev_no_auth:
    if getattr(sys, "frozen", False):
        raise RuntimeError("ARKEA_DEV_NO_AUTH no se permite en el backend empaquetado")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("ARKEA_DEV_NO_AUTH solo se permite en loopback")
    os.environ["ARKEA_API_TOKEN"] = ""
else:
    os.environ.setdefault("ARKEA_API_TOKEN", secrets.token_urlsafe(32))
if str(bundle_dir) not in sys.path:
    sys.path.insert(0, str(bundle_dir))

import uvicorn
from backend.arkea_app import app

if __name__ == "__main__":
    port = int(os.getenv("ARKEA_PORT", "7210"))
    uvicorn.run(app, host=host, port=port, reload=False, log_level="info")
