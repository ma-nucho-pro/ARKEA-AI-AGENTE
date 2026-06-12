import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    bundle_dir = Path(__file__).resolve().parent

os.environ.setdefault("ARKEA_BUNDLE_DIR", str(bundle_dir))
if str(bundle_dir) not in sys.path:
    sys.path.insert(0, str(bundle_dir))

import uvicorn
from backend.arkea_app import app

if __name__ == "__main__":
    host = os.getenv("ARKEA_HOST", "127.0.0.1")
    port = int(os.getenv("ARKEA_PORT", "7210"))
    uvicorn.run(app, host=host, port=port, reload=False, log_level="info")
