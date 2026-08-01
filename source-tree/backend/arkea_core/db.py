import os, sqlite3
from pathlib import Path
from backend.arkea_core.secrets import is_sensitive_key, protect_secret, unprotect_secret

DB_PATH = Path(os.getenv("ARKEA_DB_PATH", "./data/arkea.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE,
  value TEXT,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_connections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  api_type TEXT NOT NULL,
  provider TEXT NOT NULL,
  display_name TEXT,
  base_url TEXT,
  api_key TEXT,
  model_id TEXT,
  extra_json TEXT,
  enabled INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(api_type, provider, display_name)
);

CREATE TABLE IF NOT EXISTS app_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT,
  payload TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  folder_path TEXT,
  project_id INTEGER,
  active INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversation_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  model_used TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scope TEXT NOT NULL,
  scope_id TEXT,
  title TEXT,
  content TEXT NOT NULL,
  tags TEXT,
  source TEXT,
  importance INTEGER DEFAULT 1,
  archived INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  type TEXT DEFAULT 'general',
  folder_path TEXT NOT NULL,
  preview_path TEXT,
  active INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER,
  file_path TEXT NOT NULL,
  file_type TEXT,
  version INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  skill_id TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  folder_path TEXT NOT NULL,
  enabled INTEGER DEFAULT 1,
  permissions TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mcp_servers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  command TEXT NOT NULL,
  args TEXT,
  enabled INTEGER DEFAULT 1,
  permissions TEXT,
  requires_confirmation INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER,
  generation_type TEXT,
  prompt TEXT,
  output_path TEXT,
  preview_path TEXT,
  model_used TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS image_edits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER,
  original_image_path TEXT,
  mask_path TEXT,
  result_image_path TEXT,
  edit_prompt TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tool_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tool_name TEXT,
  input_json TEXT,
  output_json TEXT,
  status TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

DEFAULTS = {
    'app_name': 'ARKEA AI',
    'workspace': os.getenv('ARKEA_WORKSPACE', './data/projects'),
    'obsidian_vault': os.getenv('ARKEA_OBSIDIAN_VAULT', './data/obsidian_vault'),
    'user_name': 'Manu',
    'ai_mode': 'local_or_api',
    'ollama_base_url': os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434'),
    'preferred_model_chat': 'gemma3:270m',
    'preferred_model_code': 'qwen2.5-coder:0.5b',
    'preferred_model_vision': 'moondream:latest',
    'preferred_model_translation': 'gemma3:1b',
    'preferred_model_cloud': 'deepseek-v4-flash:cloud',
    'api_provider': 'custom',
    'api_base_url': '',
    'api_key': '',
    'api_model_id': '',
    'router_mode': 'auto',
    'ai_engine_mode': 'auto',
    'omniroute_base_url': 'http://127.0.0.1:20128',
    'omniroute_api_key': '',
    'omniroute_model_chat': 'auto',
    'omniroute_model_code': 'auto/coding',
    'omniroute_model_artifact': 'auto/coding',
    'omniroute_model_document': 'auto',
    'omniroute_model_file': 'auto',
    'omniroute_model_vision': 'auto',
    'omniroute_model_web_search': 'auto',
    'omniroute_model_image_generation': 'auto',
    'active_skill_id': '',
    'site_url': 'http://127.0.0.1',
    'image_api_provider': 'custom',
    'image_api_url': '',
    'image_api_key': '',
    'image_api_model_id': '',
    'elevenlabs_api_key': '',
    'elevenlabs_voice_id': '',
    'elevenlabs_voice_name': '',
    'elevenlabs_model_id': 'eleven_multilingual_v2',
    'use_elevenlabs_voice': '0',
    'input_language': 'es-ES',
    'stt_api_url': '',
    'stt_api_key': '',
    'stt_model_id': '',
    'agent_name': 'ARKEA',
    'avatar_emotion': 'neutral',
    'avatar_color_1': '#7c3aed',
    'avatar_color_2': '#06b6d4',
    'avatar_eye_color': '#ffffff',
    'avatar_mouth_color': '#e0f2fe',
    'avatar_inner_color': '#ffffff33',
    'theme_mode': 'dark',
    'ui_accent_1': '#6d5dfc',
    'ui_accent_2': '#06b6d4',
    'ui_background_custom': '/static/assets/fondoarkeaai.png',
    'avatar_path': '',
    'avatar_data_url': '',
}

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = connect()
    try:
        con.executescript(SCHEMA)
        for k, v in DEFAULTS.items():
            con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
        for row in con.execute("SELECT id,key,value FROM settings").fetchall():
            if is_sensitive_key(row["key"]) and row["value"] and not str(row["value"]).startswith("dpapi:v1:"):
                con.execute("UPDATE settings SET value=? WHERE id=?", (protect_secret(row["value"]), row["id"]))
        for row in con.execute("SELECT id,api_key FROM api_connections WHERE api_key IS NOT NULL AND api_key<>''").fetchall():
            if not str(row["api_key"]).startswith("dpapi:v1:"):
                con.execute("UPDATE api_connections SET api_key=? WHERE id=?", (protect_secret(row["api_key"]), row["id"]))
        # Repair databases produced by older builds that accidentally encrypted
        # base_url instead of api_key on INSERT.
        for row in con.execute("SELECT id,base_url FROM api_connections WHERE base_url LIKE 'dpapi:v1:%'").fetchall():
            restored_url = unprotect_secret(row["base_url"])
            if restored_url:
                con.execute("UPDATE api_connections SET base_url=? WHERE id=?", (restored_url, row["id"]))
        con.commit()
    finally:
        con.close()

def _decrypt_row(row):
    data = dict(row)
    if "api_key" in data:
        data["api_key"] = unprotect_secret(data.get("api_key") or "")
    if "key" in data and "value" in data and is_sensitive_key(data.get("key")):
        data["value"] = unprotect_secret(data.get("value") or "")
    return data

def rows(sql, params=()):
    con = connect()
    try:
        cur = con.execute(sql, params)
        return [_decrypt_row(r) for r in cur.fetchall()]
    finally:
        con.close()

def one(sql, params=()):
    con = connect()
    try:
        cur = con.execute(sql, params)
        r = cur.fetchone()
        return _decrypt_row(r) if r else None
    finally:
        con.close()

def execute(sql, params=()):
    params = list(params)
    normalized = " ".join(sql.lower().split())
    if "settings" in normalized and len(params) >= 2 and is_sensitive_key(params[0]):
        params[1] = protect_secret(params[1])
    if (
        "update api_connections set base_url=?, api_key=?" in normalized
        or "update api_connections set base_url=?,api_key=?" in normalized
    ) and len(params) >= 2:
        params[1] = protect_secret(params[1])
    if "insert into api_connections" in normalized and len(params) >= 5:
        params[4] = protect_secret(params[4])
    con = connect()
    try:
        cur = con.execute(sql, tuple(params))
        con.commit()
        return cur.lastrowid
    finally:
        con.close()

def upsert_setting(key: str, value: str):
    execute("INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)", (key, value))

def get_setting(key: str, default=None):
    r = one("SELECT value FROM settings WHERE key=?", (key,))
    if not r:
        return default
    return unprotect_secret(r['value']) if is_sensitive_key(key) else r['value']
