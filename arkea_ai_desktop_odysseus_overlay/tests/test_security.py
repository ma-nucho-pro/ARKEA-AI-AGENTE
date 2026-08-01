import asyncio
import gc
import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.arkea_core.security import read_upload_limited, safe_path, sanitize_svg, validate_outbound_url
from backend.arkea_core.secrets import is_sensitive_key, protect_secret, unprotect_secret
from backend.arkea_core import db, obsidian


class _Upload:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    async def read(self, size: int):
        chunk = self.data[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


class SecurityTests(unittest.TestCase):
    def test_frontend_preview_is_sandboxed(self):
        root = Path(__file__).resolve().parents[1]
        index = (root / "frontend" / "index.html").read_text(encoding="utf-8")
        app_js = (root / "frontend" / "app.js").read_text(encoding="utf-8")
        self.assertIn('sandbox="allow-scripts"', index)
        self.assertIn("viewer.setAttribute('sandbox'", app_js)

    def test_data_root_is_not_published(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "backend" / "arkea_app.py").read_text(encoding="utf-8")
        self.assertNotIn('app.mount("/data",', source)

    def test_local_token_protects_every_backend_route_without_html_leak(self):
        root = Path(__file__).resolve().parents[1]
        backend = (root / "backend" / "arkea_app.py").read_text(encoding="utf-8")
        desktop = (root / "desktop" / "main.js").read_text(encoding="utf-8")
        self.assertIn("if API_TOKEN:", backend)
        self.assertNotIn('request.url.path.startswith("/api/")', backend)
        self.assertNotIn("arkea-api-token", backend)
        self.assertIn("protectLocalBackendSession()", desktop)
        self.assertIn("onBeforeSendHeaders", desktop)
        self.assertIn("name.toLowerCase() === 'x-arkea-token'", desktop)
        self.assertIn("shouldAttachArkeaToken(details, TRUSTED_ORIGIN)", desktop)
        self.assertIn("details.requestHeaders['X-Arkea-Token'] = API_TOKEN", desktop)

    def test_sandboxed_preview_auth_is_media_only(self):
        root = Path(__file__).resolve().parents[1]
        helper = root / "desktop" / "request_auth.js"
        script = f"""
const {{shouldAttachArkeaToken: allow}} = require({str(helper)!r});
const origin = 'http://127.0.0.1:23456';
const cases = [
  [{{url: origin + '/', resourceType: 'mainFrame'}}, true],
  [{{url: origin + '/api/health', resourceType: 'xhr', initiator: origin}}, true],
  [{{url: origin + '/static/app.js', resourceType: 'script', frameId: 0}}, true],
  [{{url: origin + '/api/health', resourceType: 'xhr', frameId: 0}}, true],
  [{{url: origin + '/static/app.js', resourceType: 'script', frame: {{url: origin + '/', parent: null}}}}, true],
  [{{url: origin + '/data/generated/image.png', resourceType: 'image', initiator: 'null'}}, true],
  [{{url: origin + '/data/uploads/audio.mp3', resourceType: 'media', initiator: 'null'}}, true],
  [{{url: origin + '/data/generated/image.png', resourceType: 'image', frame: {{url: 'about:srcdoc', parent: {{url: origin + '/'}}}}}}, true],
  [{{url: origin + '/data/uploads/audio.mp3', resourceType: 'media', frame: {{url: 'about:srcdoc', parent: {{url: origin + '/'}}}}}}, true],
  [{{url: origin + '/api/arkea/mcp/1/toggle', resourceType: 'xhr', initiator: 'null'}}, false],
  [{{url: origin + '/', resourceType: 'subFrame', initiator: 'null'}}, false],
  [{{url: origin + '/api/health', resourceType: 'xhr', frameId: 3}}, false],
  [{{url: origin + '/', resourceType: 'subFrame', frameId: 0}}, false],
  [{{url: origin + '/api/health', resourceType: 'xhr', frame: {{url: 'about:srcdoc', parent: {{url: origin + '/'}}}}}}, false],
  [{{url: origin + '/data/generated/image.png', resourceType: 'image', frame: {{url: 'about:srcdoc', parent: {{url: 'https://evil.invalid/'}}}}}}, false],
  [{{url: origin + '/api/health', resourceType: 'image', initiator: 'null'}}, false],
  [{{url: origin + '/api/health', resourceType: 'xhr', initiator: 'https://evil.invalid'}}, false],
];
for (const [details, expected] of cases) {{
  if (allow(details, origin) !== expected) process.exit(1);
}}
"""
        completed = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_safe_path_rejects_prefixed_sibling(self):
        root = Path(tempfile.gettempdir()) / "arkea-project"
        with self.assertRaises(ValueError):
            safe_path(root, "../arkea-project-evil/file.txt")

    def test_safe_path_accepts_child(self):
        root = Path(tempfile.gettempdir()) / "arkea-project"
        expected = (root / "docs/file.txt").resolve()
        self.assertEqual(safe_path(root, "docs/file.txt"), expected)

    def test_obsidian_section_traversal_is_rejected_before_writing(self):
        for section in ("../escape", "..\\escape", "C:\\escape", "/tmp/escape"):
            with self.subTest(section=section), self.assertRaises(ValueError):
                obsidian.write_note(section, "title", "content")

    def test_ssrf_blocks_loopback_by_default(self):
        with self.assertRaises(ValueError):
            validate_outbound_url("http://127.0.0.1:7210/api/health")

    def test_ssrf_allows_only_known_loopback_service_ports(self):
        self.assertEqual(
            validate_outbound_url("http://127.0.0.1:11434/api/tags", allow_local=True),
            "http://127.0.0.1:11434/api/tags",
        )
        with self.assertRaises(ValueError):
            validate_outbound_url("http://127.0.0.1:7210/api/health", allow_local=True)

    def test_upload_limit_is_enforced(self):
        with self.assertRaises(ValueError):
            asyncio.run(read_upload_limited(_Upload(b"x" * 20), 10))

    def test_svg_active_content_is_removed(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><image href="file:///secret" onload="x()"/></svg>'
        clean = sanitize_svg(svg)
        self.assertNotIn("script", clean.lower())
        self.assertNotIn("file:///", clean.lower())
        self.assertNotIn("onload", clean.lower())

    def test_secret_round_trip(self):
        self.assertTrue(is_sensitive_key("elevenlabs_api_key"))
        protected = protect_secret("secret-value")
        if os.name == "nt":
            self.assertNotEqual(protected, "secret-value")
        self.assertEqual(unprotect_secret(protected), "secret-value")

    def test_database_encrypts_sensitive_settings(self):
        original = db.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as directory:
                db.DB_PATH = Path(directory) / "arkea.db"
                db.init_db()
                db.execute("INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)", ("service_api_key", "top-secret"))
                connection = sqlite3.connect(db.DB_PATH)
                try:
                    stored = connection.execute("SELECT value FROM settings WHERE key='service_api_key'").fetchone()[0]
                finally:
                    connection.close()
                if os.name == "nt":
                    self.assertTrue(stored.startswith("dpapi:v1:"))
                    self.assertNotIn("top-secret", stored)
                self.assertEqual(db.get_setting("service_api_key"), "top-secret")
        finally:
            db.DB_PATH = original

    def test_database_encrypts_api_key_on_insert_and_update(self):
        original = db.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as directory:
                db.DB_PATH = Path(directory) / "security.db"
                db.init_db()
                api_id = db.execute(
                    "INSERT INTO api_connections(api_type,provider,display_name,base_url,api_key,"
                    "model_id,extra_json,enabled) VALUES(?,?,?,?,?,?,?,1)",
                    ("chat", "test", "Test", "https://example.com/v1", "insert-secret", "m", "{}"),
                )
                db.execute(
                    "UPDATE api_connections SET base_url=?,api_key=?,model_id=?,extra_json=?,"
                    "enabled=1,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    ("https://example.com/v1", "update-secret", "m", "{}", api_id),
                )
                connection = sqlite3.connect(db.DB_PATH)
                try:
                    raw = connection.execute(
                        "SELECT base_url,api_key FROM api_connections WHERE id=?", (api_id,)
                    ).fetchone()
                finally:
                    connection.close()
                self.assertEqual(raw[0], "https://example.com/v1")
                self.assertNotEqual(raw[1], "update-secret")
                self.assertEqual(db.one("SELECT api_key FROM api_connections WHERE id=?", (api_id,))["api_key"], "update-secret")
                gc.collect()
        finally:
            db.DB_PATH = original


if __name__ == "__main__":
    unittest.main()
