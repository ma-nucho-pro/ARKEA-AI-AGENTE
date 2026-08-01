from backend.arkea_core.db import execute, rows

def save_memory(scope: str, content: str, title: str = "", scope_id: str = "", tags: str = "", source: str = "manual", importance: int = 1):
    return execute(
        "INSERT INTO memories(scope,scope_id,title,content,tags,source,importance) VALUES(?,?,?,?,?,?,?)",
        (scope, scope_id, title, content, tags, source, importance),
    )

def list_memory(scope: str | None = None, scope_id: str | None = None):
    sql = "SELECT * FROM memories WHERE archived=0"
    params = []
    if scope:
        sql += " AND scope=?"; params.append(scope)
    if scope_id:
        sql += " AND scope_id=?"; params.append(scope_id)
    sql += " ORDER BY importance DESC, created_at DESC"
    return rows(sql, tuple(params))

def archive_memory(memory_id: int):
    return execute("UPDATE memories SET archived=1, updated_at=CURRENT_TIMESTAMP WHERE id=?", (memory_id,))
