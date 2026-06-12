import os, sqlite3
from pathlib import Path

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
    with connect() as con:
        con.executescript(SCHEMA)
        for k, v in DEFAULTS.items():
            con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
        con.commit()

def rows(sql, params=()):
    with connect() as con:
        cur = con.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

def one(sql, params=()):
    with connect() as con:
        cur = con.execute(sql, params)
        r = cur.fetchone()
        return dict(r) if r else None

def execute(sql, params=()):
    with connect() as con:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid

def upsert_setting(key: str, value: str):
    execute("INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)", (key, value))

def get_setting(key: str, default=None):
    r = one("SELECT value FROM settings WHERE key=?", (key,))
    return r['value'] if r else default
