import os, platform, shutil

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None


def get_hardware_profile():
    ram_gb = 0
    free_disk_gb = 0
    cpu_count = os.cpu_count() or 1
    if psutil:
        try:
            ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
        except Exception:
            ram_gb = 0
    try:
        usage = shutil.disk_usage(os.path.expanduser('~'))
        free_disk_gb = round(usage.free / (1024**3), 1)
    except Exception:
        pass
    return {
        'os': platform.system(),
        'os_version': platform.version(),
        'machine': platform.machine(),
        'cpu_count': cpu_count,
        'ram_gb': ram_gb,
        'free_disk_gb': free_disk_gb,
    }


def tier_from_ram(ram_gb: float):
    if ram_gb and ram_gb < 8:
        return 'muy_bajo'
    if ram_gb and ram_gb < 12:
        return 'bajo'
    if ram_gb and ram_gb < 24:
        return 'medio'
    return 'alto'
