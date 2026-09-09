import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from backend import Bridge, StreamParser, build_command
from agent_session import RpcSession, SessionLease
from agents.claude import ClaudeSession
from agents.codex import CodexSession
from permission_modes import MODES, codex_permissions, permission_args, session_options
import test_native


class PermissionModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.events = []
        self.bridge = Bridge(self.temp.name, self.events.append)
        self.bridge.new()
        self.bridge.current["agent"] = "claude"

    def tearDown(self):
        self.bridge.close()
        self.temp.cleanup()

    def select(self, mode, **values):
        self.bridge.dispatch(dict(action="permission_mode", mode=mode,
                                  chatId=self.bridge.current["id"], **values))

    def test_saved_per_chat_clears_bash_override_and_keeps_global_defaults(self):
        self.bridge.current["bashApproval"] = "always"
        self.select("acceptEdits")
        identity = self.bridge.current["id"]
        self.assertNotIn("bashApproval", self.bridge.current)
        self.assertNotIn("permissionMode", self.bridge.settings)
        self.bridge.close()
        self.bridge = Bridge(self.temp.name, self.events.append)
        self.assertEqual(self.bridge.current["permissionMode"], "acceptEdits")
        self.bridge.new()
        self.assertNotIn("permissionMode", self.bridge.current)
        self.bridge.dispatch({"action": "open", "id": identity})
        self.assertEqual(self.bridge.current["permissionMode"], "acceptEdits")

    def test_failed_save_does_not_change_mode_or_close_session(self):
        previous = copy.deepcopy(self.bridge.current)
        rpc = MagicMock()
        self.bridge.rpc = rpc
        with patch.object(self.bridge, "save", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.select("bypassPermissions")
        self.assertEqual(self.bridge.current, previous)
        rpc.close.assert_not_called()

    def test_busy_terminal_pending_and_stale_requests_cannot_change_mode(self):
        self.bridge.busy = True
        with self.assertRaises(ValueError): self.select("auto")
        self.bridge.busy = False
        with patch.object(self.bridge, "terminal_state", return_value=True):
            with self.assertRaises(ValueError): self.select("auto")
        self.bridge.ui_requests = [{"id": "pending"}]
        with self.assertRaises(ValueError): self.select("auto")
        self.bridge.ui_requests = []
        for identity in ("stale", None):
            with self.assertRaises(ValueError):
                self.bridge.set_permission_mode({"mode": "auto", "chatId": identity})
        self.assertNotIn("permissionMode", self.bridge.current)

    def test_modes_are_validated_for_agent_and_not_interpolated_into_argv(self):
        for mode in ("yolo", "--dangerous", {}, None):
            with self.assertRaises(ValueError): self.select(mode)
        self.assertNotIn("permissionMode", self.bridge.current)

    def test_folder_change_resets_mode_but_model_change_preserves_it(self):
        self.select("plan")
        self.bridge.dispatch({"action": "settings", "settings": {"model": "other"}})
        self.assertEqual(self.bridge.current["permissionMode"], "plan")
        self.bridge.dispatch({"action": "settings", "settings": {"cwd": self.temp.name}})
        self.assertNotIn("permissionMode", self.bridge.current)

    def test_mode_can_be_selected_before_a_chat_exists(self):
        self.bridge.current = None
        with patch.object(self.bridge, "default_agent", return_value="pi"):
            self.bridge.set_permission_mode({"mode": "ask", "chatId": None})
        self.assertEqual(self.bridge.current["agent"], "pi")
        self.assertEqual(session_options(self.bridge.current)["_permission_mode"], "ask")

    def test_unsupported_first_mode_does_not_create_a_chat(self):
        self.bridge.current = None
        with patch.object(self.bridge, "default_agent", return_value="pi"):
            with self.assertRaises(ValueError):
                self.bridge.set_permission_mode({"mode": "bypassPermissions"})
        self.assertIsNone(self.bridge.current)


class PermissionAdapterTests(unittest.TestCase):
    def test_codex_start_resume_and_fork_send_verified_protocol_values(self):
        for mode in ("default", "workspace", "auto-review", "full-access", "read-only"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                session_path = Path(temp) / "native.jsonl"
                session_path.write_text(json.dumps({"type": "session_meta", "payload": {"id": "native"}}))
                for resume in (None, session_path):
                    calls = []
                    def call(_session, method, params=None, **kwargs):
                        calls.append((method, params))
                        return {"thread": {"id": "native", "path": str(session_path)},
                                "approvalPolicy": "on-request", "approvalsReviewer": "user"}
                    with patch("agents.codex.cli_binary", return_value="codex"), \
                         patch("agents.codex.subprocess.Popen"), patch("agents.codex.threading.Thread"), \
                         patch.object(CodexSession, "call", call):
                        session = CodexSession("codex", temp, {"cwd": temp, "_permission_mode": mode}, resume)
                        try:
                            method, params = calls[-1]
                            self.assertEqual(method, "thread/resume" if resume else "thread/start")
                            for key, value in codex_permissions(mode).items(): self.assertEqual(params[key], value)
                            if mode == "default":
                                self.assertNotIn("sandbox", params)
                                if resume:
                                    self.assertEqual(params["approvalPolicy"], "on-request")
                                    self.assertEqual(params["approvalsReviewer"], "user")
                                    self.assertTrue(any(p.get("ephemeral") for m, p in calls if m == "thread/start"))
                                else: self.assertNotIn("approvalPolicy", params)
                            session.request("fork", entryId="turn")
                            for key, value in codex_permissions(mode).items(): self.assertEqual(calls[-1][1][key], value)
                        finally: session.close()
        self.assertEqual(codex_permissions("full-access")["sandbox"], "danger-full-access")
        self.assertEqual(codex_permissions("workspace")["approvalPolicy"], "on-request")
        self.assertEqual(codex_permissions("read-only")["approvalPolicy"], "never")

    def test_claude_explicit_bypass_is_only_used_when_selected(self):
        for entry in MODES["claude"]:
            mode = entry["id"]
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp, \
                 patch("agents.claude.cli_binary", return_value="claude"), \
                 patch("agents.claude.subprocess.Popen") as spawn, patch("agents.claude.threading.Thread"), \
                 patch.object(ClaudeSession, "call", return_value={}):
                session = ClaudeSession("claude", temp, {"cwd": temp, "_permission_mode": mode})
                try:
                    argv = spawn.call_args.args[0]
                    self.assertEqual("--dangerously-skip-permissions" in argv, mode == "bypassPermissions")
                    self.assertNotIn("--allow-dangerously-skip-permissions", argv)
                    if mode == "default": self.assertNotIn("--permission-mode", argv)
                    if mode == "manual": self.assertEqual(argv[argv.index("--permission-mode") + 1], "default")
                finally: session.close()

    def test_opencode_auto_uses_native_flag_and_preserves_deny_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            for mode in ("default", "auto"):
                argv, _, env, _ = build_command("opencode", "hello", [], {"_permission_mode": mode}, Path(temp) / "prompt")
                self.assertEqual("--auto" in argv, mode == "auto")
                if mode == "auto": self.assertNotIn("OPENCODE_PERMISSION", env)
                else: self.assertEqual(json.loads(env["OPENCODE_PERMISSION"]), {"*": "deny"})

    def test_pi_gate_is_explicit_and_invalid_modes_release_ownership(self):
        self.assertEqual(permission_args("pi", "default"), [])
        self.assertTrue(Path(permission_args("pi", "ask")[1]).is_file())
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError): RpcSession("pi", temp, {"cwd": temp, "_permission_mode": "yolo"})
            SessionLease(temp).close()

    def test_pi_does_not_start_a_turn_if_approval_extension_failed_to_load(self):
        with tempfile.TemporaryDirectory() as temp, patch("agent_session.cli_binary", return_value="pi"), \
             patch("agent_session.subprocess.Popen"), patch("agent_session.threading.Thread"), \
             patch.object(RpcSession, "request", return_value={"commands": []}):
            with self.assertRaisesRegex(ValueError, "could not load"):
                RpcSession("pi", temp, {"cwd": temp, "_permission_mode": "ask"})
            SessionLease(temp).close()

    def test_codex_default_terminal_policy_preserves_granular_rules(self):
        import tomllib
        policy = {"granular": {"sandbox_approval": True, "rules": False, "mcp_elicitations": True}}
        args = permission_args("codex", "default", {"approvalPolicy": policy, "approvalsReviewer": "user"})
        self.assertEqual(tomllib.loads(args[1])["approval_policy"], policy)

    def test_opencode_completed_and_denied_tool_activity_is_visible(self):
        parser = StreamParser("opencode")
        for status in ("completed", "error"):
            parser.feed(json.dumps({"type": "tool_use", "part": {"callID": "call-1", "tool": "bash",
                "state": {"status": status, "input": {"command": "ls"}, "output": "fixture.txt", "error": "Denied" if status == "error" else ""}}}))
            self.assertEqual(len(parser.tools), 1)
            self.assertEqual(parser.tools[0]["args"]["command"], "ls")
            self.assertEqual(parser.tools[0]["status"], "complete" if status == "completed" else "error")
        self.assertEqual(parser.tools[0]["output"], "Denied")
        self.assertFalse(parser.text)


class PermissionReconnectTests(unittest.TestCase):
    # Use the actual pipe-based fixture to verify saved options reach a resumed CLI.
    setUp = test_native.NativeTests.setUp
    tearDown = test_native.NativeTests.tearDown

    def test_mode_change_resumes_existing_history_with_new_launch_flags(self):
        self.bridge.send({"text": "first"})
        self.bridge.worker.join(timeout=10)
        path = self.bridge.current["native"]["sessionFile"]
        self.bridge.set_permission_mode({"chatId": self.bridge.current["id"], "mode": "write"})
        self.assertIsNone(self.bridge.rpc)
        self.bridge.send({"text": "second"})
        self.bridge.worker.join(timeout=10)
        self.assertFalse(self.bridge.busy)
        self.assertEqual(self.bridge.current["native"]["sessionFile"], path)
        argv = self.bridge.rpc.proc.args
        self.assertEqual(argv[argv.index("--approval-mode") + 1], "write")
        self.assertEqual(len(self.bridge.current["messages"]), 4)


if __name__ == "__main__":
    unittest.main()
