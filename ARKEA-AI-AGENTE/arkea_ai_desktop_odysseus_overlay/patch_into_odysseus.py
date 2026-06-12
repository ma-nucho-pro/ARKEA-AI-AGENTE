import argparse, shutil, pathlib, re

parser = argparse.ArgumentParser()
parser.add_argument('--odysseus', required=True, help='Ruta del repo Odysseus clonado')
args = parser.parse_args()
root = pathlib.Path(__file__).resolve().parent
ody = pathlib.Path(args.odysseus).resolve()
if not ody.exists():
    raise SystemExit('No existe la ruta de Odysseus')

# Copiar carpetas ARKEA sin borrar Odysseus
for folder in ['backend', 'frontend', 'desktop', 'data/skills', 'config', 'scripts']:
    src = root / folder
    dst = ody / folder
    if src.exists():
        if dst.exists() and folder in ['backend', 'frontend']:
            # fusiona archivos
            for p in src.rglob('*'):
                if p.is_file():
                    rel = p.relative_to(src)
                    target = dst / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, target)
        else:
            shutil.copytree(src, dst, dirs_exist_ok=True)

# Copiar starter y docs
for fname in ['start_arkea.py', 'requirements.txt', '.env.example', 'ODYSSEUS_PATCH_GUIDE.md']:
    src = root / fname
    if src.exists(): shutil.copy2(src, ody / f'ARKEA_{fname}' if fname == 'requirements.txt' else ody / fname)

print('Overlay ARKEA copiado. Ejecuta python start_arkea.py para probar modo standalone o integra rutas en app.py de Odysseus.')
