from pathlib import Path
import json
from backend.arkea_core.db import init_db, execute

init_db()
for mf in Path('data/skills').glob('*/manifest.json'):
    data = json.loads(mf.read_text(encoding='utf-8'))
    execute('INSERT OR REPLACE INTO skills(skill_id,name,description,folder_path,permissions) VALUES(?,?,?,?,?)',
            (data['id'], data['name'], data.get('description',''), str(mf.parent), json.dumps(data.get('permissions', []))))
    print('installed', data['id'])
