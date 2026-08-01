import argparse, shutil, pathlib, re

parser = argparse.ArgumentParser()
parser.add_argument('--odysseus', required=True, help='Ruta del repo Odysseus clonado')
args = parser.parse_args()
root = pathlib.Path(__file__).resolve().parent
ody = pathlib.Path(args.odysseus).resolve()
if not ody.exists():
    raise SystemExit('No existe la ruta de Odysseus')

IGNORED_PARTS = {
    'node_modules', 'dist', 'backend-dist', '__pycache__', '.pytest_cache',
    '.venv', '_work', 'release',
}

def ignored_tree(_directory, names):
    return [name for name in names if name in IGNORED_PARTS]

# Copiar carpetas ARKEA sin borrar Odysseus
for folder in ['backend', 'frontend', 'desktop', 'data/skills', 'config', 'scripts']:
    src = root / folder
    dst = ody / folder
    if src.exists():
        if dst.exists() and folder in ['backend', 'frontend']:
            # fusiona archivos
            for p in src.rglob('*'):
                if p.is_file() and not any(part in IGNORED_PARTS for part in p.relative_to(src).parts):
                    rel = p.relative_to(src)
                    target = dst / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, target)
        else:
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignored_tree)

# Copiar starter y docs
for fname in ['start_arkea.py', 'requirements.txt', 'requirements-lock.txt', '.env.example', 'ODYSSEUS_PATCH_GUIDE.md']:
    src = root / fname
    if src.exists(): shutil.copy2(src, ody / f'ARKEA_{fname}' if fname == 'requirements.txt' else ody / fname)

print('Overlay ARKEA copiado. Usa scripts/start_windows.bat solo para desarrollo local o integra las rutas en Odysseus.')
