from pathlib import Path

DANGEROUS_PATH_PARTS = ["..", "~", "$HOME", "%USERPROFILE%"]

def safe_path(root: str | Path, relative: str | Path) -> Path:
    root = Path(root).resolve()
    target = (root / relative).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("Ruta fuera del workspace permitido")
    return target

def is_sensitive_command(cmd: str) -> bool:
    blocked = ["rm -rf", "format ", "del /s", "shutdown", "reboot", "mkfs", ":(){ :|:& };:"]
    low = cmd.lower()
    return any(x in low for x in blocked)
