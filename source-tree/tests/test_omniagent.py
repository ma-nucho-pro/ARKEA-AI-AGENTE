import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

from backend.arkea_core import agent_runtime, image_lab, mcp_runtime, model_router, omniroute
from backend.arkea_core.security import validate_outbound_url
from backend.routes import vision


class OmniRouteSecurityTests(unittest.TestCase):
    def test_only_supported_omniroute_versions_are_accepted(self):
        self.assertFalse(omniroute._supported_version("3.8.48"))
        self.assertTrue(omniroute._supported_version("3.8.49"))
        self.assertTrue(omniroute._supported_version("3.9.0"))
        self.assertTrue(omniroute._supported_version("4.0.0"))
        self.assertFalse(omniroute._supported_version("not-a-version"))

    def test_desktop_uses_visible_official_installer_flow(self):
        main_js = (Path(__file__).parents[1] / "desktop" / "main.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("OmniRoute.Setup.3.8.49.exe", main_js)
        self.assertIn("shell.openExternal(OMNIROUTE.url)", main_js)
        self.assertIn("shell.openPath(downloadedInstaller)", main_js)
        self.assertNotIn("downloadVerifiedFile", main_js)
        self.assertNotIn("verifyManagedOmniroute", main_js)

    def test_only_exact_loopback_origin_is_accepted(self):
        self.assertEqual(omniroute._origin("http://localhost:20128/"), "http://localhost:20128")
        self.assertEqual(omniroute._origin("http://[::1]:20128"), "http://[::1]:20128")
        rejected = (
            "https://localhost:20128",
            "http://127.0.0.1:20129",
            "http://192.168.1.10:20128",
            "http://localhost:20128/v1",
            "http://user@localhost:20128",
            "http://localhost:20128?next=evil",
        )
        for value in rejected:
            with self.subTest(value=value), self.assertRaises(ValueError):
                omniroute._origin(value)

    def test_ssrf_policy_allows_only_the_known_omniroute_port(self):
        self.assertEqual(
            validate_outbound_url("http://127.0.0.1:20128/v1/models", allow_local=True),
            "http://127.0.0.1:20128/v1/models",
        )
        with self.assertRaises(ValueError):
            validate_outbound_url("http://127.0.0.1:20129/v1/models", allow_local=True)
        with self.assertRaises(ValueError):
            validate_outbound_url("http://192.168.1.10:20128/v1/models", allow_local=True)

    @patch.object(omniroute, "get_setting")
    def test_api_key_is_never_returned_by_settings(self, get_setting):
        values = {
            "omniroute_api_key": "top-secret",
            "ai_engine_mode": "auto",
            "omniroute_base_url": "http://127.0.0.1:20128",
        }
        get_setting.side_effect = lambda key, default="": values.get(key, default)
        result = omniroute.settings()
        self.assertTrue(result["api_key_configured"])
        self.assertNotIn("api_key", result)
        self.assertNotIn("top-secret", json.dumps(result))

    @patch.object(omniroute, "get_setting", return_value="")
    def test_internal_api_key_can_be_supplied_only_by_process_environment(self, _setting):
        with patch.dict(os.environ, {"OMNIROUTE_API_KEY": "sk-process-secret"}):
            self.assertEqual(omniroute.api_key(), "sk-process-secret")
            self.assertEqual(
                omniroute.headers()["Authorization"],
                "Bearer sk-process-secret",
            )

    @patch.object(omniroute, "_origin", return_value="http://127.0.0.1:20128")
    @patch.object(omniroute, "guarded_request")
    def test_health_rejects_unverified_json_on_the_expected_port(self, request, _origin):
        response = MagicMock(status_code=200)
        response.json.return_value = {"ok": True}
        request.return_value = response
        with patch.object(omniroute, "headers", return_value={"Authorization": "Bearer test"}):
            result = omniroute.status()
        self.assertFalse(result["running"])
        self.assertIn("identidad", result["error"])
        request.assert_called_once()


class RoutingModeTests(unittest.TestCase):
    @patch.object(model_router, "enrich_system_prompt", side_effect=lambda value, _task: value)
    @patch.object(model_router, "chat_local", return_value="LOCAL")
    @patch.object(model_router, "ranked_apis", return_value=[])
    @patch.object(model_router, "get_setting", return_value="free")
    def test_free_mode_never_falls_back_to_ollama(
        self, _setting, _ranked, chat_local, _enrich
    ):
        result = model_router.route_text("hola")
        self.assertIn("modo Gratis es estricto", result)
        chat_local.assert_not_called()

    @patch.object(model_router, "enrich_system_prompt", side_effect=lambda value, _task: value)
    @patch.object(model_router, "chat_local", return_value="LOCAL")
    @patch.object(model_router, "ranked_apis", return_value=[])
    @patch.object(model_router, "get_setting", return_value="direct")
    def test_direct_mode_never_falls_back_to_other_engines(
        self, _setting, _ranked, chat_local, _enrich
    ):
        result = model_router.route_text("hola")
        self.assertIn("API directa", result)
        chat_local.assert_not_called()

    @patch.object(model_router.omniroute, "remember_decision")
    @patch.object(model_router, "enrich_system_prompt", side_effect=lambda value, _task: value)
    @patch.object(model_router, "chat_local", return_value="LOCAL")
    @patch.object(model_router, "ranked_apis", return_value=[])
    @patch.object(model_router, "get_setting", return_value="auto")
    def test_auto_mode_has_visible_local_fallback(
        self, _setting, _ranked, _chat_local, _enrich, remember
    ):
        self.assertEqual(model_router.route_text("hola"), "LOCAL")
        remember.assert_called_once()

    @patch.object(image_lab, "_try_custom_image_api", return_value=("secret.png", "/secret.png"))
    def test_free_and_local_image_modes_never_call_direct_image_api(self, custom_api):
        self.assertIsNone(image_lab._try_custom_image_api_for_mode("imagen", "free"))
        self.assertIsNone(image_lab._try_custom_image_api_for_mode("imagen", "local"))
        custom_api.assert_not_called()
        self.assertEqual(
            image_lab._try_custom_image_api_for_mode("imagen", "direct"),
            ("secret.png", "/secret.png"),
        )
        custom_api.assert_called_once_with("imagen", allow_local=False)

    @patch.object(model_router, "rows")
    @patch.object(model_router, "get_setting", return_value="direct")
    def test_direct_candidates_exclude_ollama_and_loopback(self, _setting, rows):
        rows.return_value = [
            {"provider": "ollama_local", "base_url": "http://127.0.0.1:11434/v1", "model_id": "gemma"},
            {"provider": "openai", "base_url": "https://api.openai.com/v1/chat/completions", "model_id": "gpt"},
        ]
        result = model_router._enabled_candidates("chat")
        self.assertEqual([item["provider"] for item in result], ["openai"])

    def test_direct_image_candidates_exclude_local_and_loopback(self):
        self.assertFalse(
            image_lab._is_direct_image_provider(
                {
                    "provider": "comfyui_local",
                    "base_url": "http://127.0.0.1:8188",
                }
            )
        )
        self.assertTrue(
            image_lab._is_direct_image_provider(
                {
                    "provider": "stability",
                    "base_url": "https://api.stability.ai/v2/generate",
                }
            )
        )

    @patch.object(image_lab, "_try_api_connections_image", return_value=None)
    @patch.object(image_lab, "_try_custom_image_api", return_value=None)
    @patch.object(image_lab, "_setting", return_value="free")
    def test_free_image_mode_returns_error_instead_of_local_placeholder(
        self, _setting, _custom, _connections
    ):
        result = image_lab.generate_placeholder_image("prueba")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "omniroute_image_unavailable")

    @patch.object(vision.ollama, "status")
    @patch.object(vision, "_candidate_vision_apis", return_value=[])
    @patch.object(vision, "get_setting", return_value="direct")
    def test_direct_vision_never_falls_back_to_ollama(self, _setting, _apis, ollama_status):
        result = vision.analyze(
            vision.VisionIn(image_data_url="data:image/png;base64,AA==", prompt="describe")
        )
        self.assertEqual(result["status"], "direct_vision_unavailable")
        ollama_status.assert_not_called()


class AgentContextTests(unittest.TestCase):
    @patch.object(agent_runtime, "rows")
    @patch.object(agent_runtime, "get_setting", return_value="")
    def test_selected_skill_is_scoped_to_the_request(self, _setting, rows):
        rows.return_value = []
        self.assertEqual(agent_runtime.active_skill_id(), "")
        with agent_runtime.agent_request_context("skill-demo"):
            self.assertEqual(agent_runtime.active_skill_id(), "skill-demo")
        self.assertEqual(agent_runtime.active_skill_id(), "")

    @patch.object(mcp_runtime, "call_tool", return_value={"content": "real"})
    @patch.object(mcp_runtime, "list_tools", return_value=[
        {"name": "read_file", "description": "Lee un archivo", "inputSchema": {"type": "object"}}
    ])
    @patch.object(agent_runtime, "rows")
    def test_autonomous_mcp_catalog_has_real_execution_path(self, rows, _list_tools, call_tool):
        rows.return_value = [
            {"id": 7, "name": "files", "permissions": '["execute","read","filesystem"]'}
        ]
        tools = agent_runtime.model_mcp_tools()
        alias = tools[0]["function"]["name"]
        self.assertEqual(
            agent_runtime.execute_mcp_model_tool(alias, {"path": "demo.txt"}),
            {"content": "real"},
        )
        call_tool.assert_called_once_with(7, "read_file", {"path": "demo.txt"}, confirmed=False)

    @patch.object(mcp_runtime, "list_tools", return_value=[
        {"name": "foo.bar", "inputSchema": {"type": "object"}},
        {"name": "foo/bar", "inputSchema": {"type": "object"}},
        {"name": "x" * 60 + ".one", "inputSchema": {"type": "object"}},
        {"name": "x" * 60 + "/two", "inputSchema": {"type": "object"}},
    ])
    @patch.object(agent_runtime, "rows")
    def test_mcp_aliases_remain_unique_after_sanitizing_and_truncating(self, rows, _list_tools):
        rows.return_value = [
            {"id": 9, "name": "collision", "permissions": '["execute"]'}
        ]
        tools = agent_runtime.model_mcp_tools()
        aliases = [item["function"]["name"] for item in tools]
        self.assertEqual(len(aliases), 4)
        self.assertEqual(len(set(aliases)), 4)
        self.assertTrue(all(len(alias) <= 64 for alias in aliases))


class MCPRuntimeTests(unittest.TestCase):
    def test_shell_commands_are_rejected(self):
        for command in ("cmd.exe", "powershell.exe", "node.exe & calc.exe", ""):
            with self.subTest(command=command), self.assertRaises(mcp_runtime.MCPRuntimeError):
                mcp_runtime._validated_command(command)
        self.assertEqual(mcp_runtime._validated_command("npx.cmd"), "npx.cmd")

    def test_argument_bounds_and_json_are_enforced(self):
        with self.assertRaises(mcp_runtime.MCPRuntimeError):
            mcp_runtime._decode_args("not-json")
        with self.assertRaises(mcp_runtime.MCPRuntimeError):
            mcp_runtime._decode_args(json.dumps(["x"] * 81))
        self.assertEqual(mcp_runtime._decode_args('["--stdio"]'), ["--stdio"])

    def test_both_mcp_stdio_encodings_are_parsed(self):
        line = b'{"jsonrpc":"2.0","id":2,"result":{"tools":[]}}\n'
        self.assertEqual(mcp_runtime._parse_messages(line)[0]["id"], 2)
        body = '{"jsonrpc":"2.0","id":2,"result":{"ok":true}}'
        framed = f"Content-Length: {len(body)}\r\n\r\n{body}".encode()
        self.assertTrue(mcp_runtime._parse_messages(framed)[0]["result"]["ok"])
        unicode_body = '{"jsonrpc":"2.0","id":2,"result":{"text":"visión"}}'.encode("utf-8")
        unicode_frame = b"Content-Length: " + str(len(unicode_body)).encode() + b"\r\n\r\n" + unicode_body
        self.assertEqual(mcp_runtime._parse_messages(unicode_frame)[0]["result"]["text"], "visión")

    @patch.object(mcp_runtime, "_server")
    def test_sensitive_tool_requires_explicit_confirmation(self, server):
        server.return_value = {"requires_confirmation": 1, "name": "demo"}
        with self.assertRaises(mcp_runtime.MCPConfirmationRequired):
            mcp_runtime.call_tool(1, "write", {}, confirmed=False)

    @patch.object(mcp_runtime, "_server")
    def test_tool_input_size_is_bounded(self, server):
        server.return_value = {"requires_confirmation": 0, "name": "demo"}
        with self.assertRaises(mcp_runtime.MCPRuntimeError):
            mcp_runtime.call_tool(1, "write", {"data": "x" * (1024 * 1024 + 1)})

    @patch.object(mcp_runtime, "_server")
    def test_mcp_permissions_are_enforced(self, server):
        server.return_value = {
            "requires_confirmation": 0,
            "name": "demo",
            "permissions": '["read"]',
        }
        with self.assertRaises(mcp_runtime.MCPPermissionDenied):
            mcp_runtime.call_tool(1, "write_file", {"path": "demo.txt", "data": "x"})

    @patch.object(mcp_runtime, "_server")
    def test_every_mcp_tool_requires_execute_permission(self, server):
        server.return_value = {
            "requires_confirmation": 0,
            "name": "demo",
            "permissions": '["read","filesystem"]',
        }
        with self.assertRaisesRegex(mcp_runtime.MCPPermissionDenied, "execute"):
            mcp_runtime.call_tool(1, "read_file", {"path": "demo.txt"})

    @patch.object(mcp_runtime.subprocess, "Popen")
    @patch.object(mcp_runtime, "_server")
    def test_mcp_discovery_rejects_legacy_server_without_execute(self, server, popen):
        server.return_value = {
            "name": "legacy",
            "command": "node",
            "args": "[]",
            "permissions": '["read","filesystem"]',
        }
        with self.assertRaisesRegex(mcp_runtime.MCPPermissionDenied, "execute"):
            mcp_runtime.list_tools(1)
        popen.assert_not_called()

    def test_mcp_permission_classifier_is_conservative(self):
        self.assertEqual(
            mcp_runtime._required_permissions("open_file", {}),
            {"execute", "read", "filesystem"},
        )
        self.assertTrue(
            {"execute", "read", "write"}.issubset(
                mcp_runtime._required_permissions("copy_file", {})
            )
        )
        self.assertTrue(
            {"execute", "read", "write", "network"}.issubset(
                mcp_runtime._required_permissions("download_file", {})
            )
        )
        self.assertTrue(
            {"execute", "read", "write", "network"}.issubset(
                mcp_runtime._required_permissions("upload_file", {})
            )
        )
        for name in ("save_file", "append_file", "rename_file"):
            with self.subTest(name=name):
                self.assertIn("write", mcp_runtime._required_permissions(name, {}))

    def test_rpc_output_is_stopped_at_the_memory_limit(self):
        server = {
            "command": sys.executable,
            "args": json.dumps(["-c", "import sys;sys.stdout.write('x'*2200000)"]),
            "permissions": '["execute"]',
        }
        with self.assertRaisesRegex(mcp_runtime.MCPRuntimeError, "superó el límite"):
            mcp_runtime._rpc(server, "tools/list", {}, timeout_seconds=10)


if __name__ == "__main__":
    unittest.main()
