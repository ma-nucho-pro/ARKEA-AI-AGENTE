from pathlib import Path
from backend.arkea_core.db import execute, rows, one
from backend.arkea_core.workspace import get_workspace, slugify


def _unique_folder(base: Path, title: str) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    folder = base / slugify(title)
    original = folder
    i = 1
    while folder.exists():
        i += 1
        folder = Path(str(original) + f'-{i}')
    return folder


def create_conversation(title: str = 'Nuevo chat', project_id: int | None = None, folder_path: str | None = None):
    if folder_path:
        folder = Path(folder_path).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
    else:
        folder = _unique_folder(get_workspace() / '_chats', title)
        folder.mkdir(parents=True, exist_ok=True)
    execute('UPDATE conversations SET active=0')
    cid = execute('INSERT INTO conversations(title,folder_path,project_id,active) VALUES(?,?,?,1)', (title, str(folder), project_id,))
    # Keep a tiny marker so users can see the chat folder belongs to ARKEA.
    try:
        marker = folder / 'ARKEA_CHAT_INFO.md'
        if not marker.exists():
            marker.write_text(f'# {title}\n\nCarpeta de trabajo de ARKEA AI Desktop.\n', encoding='utf-8')
    except Exception:
        pass
    return {'id': cid, 'title': title, 'folder_path': str(folder), 'project_id': project_id, 'active': 1}


def list_conversations():
    return rows('SELECT * FROM conversations ORDER BY updated_at DESC, id DESC')


def get_or_create_active(title_hint='Nuevo chat'):
    r = one('SELECT * FROM conversations WHERE active=1 ORDER BY id DESC LIMIT 1')
    if r:
        return r
    return create_conversation(title_hint)


def set_active(conversation_id: int):
    execute('UPDATE conversations SET active=0')
    execute('UPDATE conversations SET active=1, updated_at=CURRENT_TIMESTAMP WHERE id=?', (conversation_id,))
    return one('SELECT * FROM conversations WHERE id=?', (conversation_id,))


def save_message(conversation_id: int, role: str, content: str, model_used: str = ''):
    mid = execute('INSERT INTO conversation_messages(conversation_id,role,content,model_used) VALUES(?,?,?,?)', (conversation_id, role, content, model_used))
    execute('UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?', (conversation_id,))
    # Also save a visible transcript in the chat folder.
    try:
        c = one('SELECT folder_path FROM conversations WHERE id=?', (conversation_id,))
        if c and c.get('folder_path'):
            p = Path(c['folder_path']) / 'chat.md'
            with p.open('a', encoding='utf-8') as f:
                f.write(f'\n\n## {role}\n\n{content}\n')
    except Exception:
        pass
    return mid


def get_messages(conversation_id: int):
    return rows('SELECT * FROM conversation_messages WHERE conversation_id=? ORDER BY id ASC', (conversation_id,))
