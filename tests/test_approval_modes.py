import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import Bridge
from test_adapters import claude, codex


class ApprovalModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.events = []
        self.bridge = Bridge(self.temp.name, self.events.append)
        self.bridge.new()
        self.bridge.current["agent"] = "claude"
        self.session = claude()
        self.session.close = lambda: None
        self.session.ui_callback = self.bridge.native_ui
        self.bridge.rpc = self.session
        self.bridge.rpc_chat = self.bridge.current["id"]

    def tearDown(self):
        self.bridge.close()
        self.temp.cleanup()

    def prompt(self, identity="bash-1", tool="Bash", **values):
        self.session.prompt({"request_id": identity, "request": {
            "subtype": "can_use_tool", "tool_name": tool,
            "input": {"command": "printf fixture"}, **values}})

    def set_mode(self, mode):
        self.bridge.dispatch({"action": "bash_approval", "mode": mode,
                              "chatId": self.bridge.current["id"]})

    def test_always_button_approves_waiting_and_future_bash_without_cli_rules(self):
        self.prompt()
        self.assertTrue(self.bridge.ui_requests[0]["allowAlwaysBash"])
        self.assertFalse(self.session.sent)
        self.bridge.dispatch({"action": "agent_ui_response", "id": "bash-1", "confirmed": True,
                              "alwaysAllowBash": True, "chatId": self.bridge.current["id"]})
        self.assertEqual(self.bridge.current["bashApproval"], "always")
        self.assertFalse(self.bridge.ui_requests)
        self.prompt("bash-2")
        self.assertFalse(self.bridge.ui_requests)
        self.assertEqual(len(self.session.sent), 2)
        for response in self.session.sent:
            self.assertEqual(response["response"]["response"], {
                "behavior": "allow", "updatedInput": {"command": "printf fixture"}})

    def test_preference_can_approve_queued_commands_and_is_immediately_revocable(self):
        self.prompt("one")
        self.prompt("two")
        self.set_mode("always")
        self.assertEqual(len(self.session.sent), 2)
        self.assertFalse(self.bridge.ui_requests)
        self.set_mode("ask")
        self.prompt("three")
        self.assertEqual(len(self.session.sent), 2)
        self.assertEqual(self.bridge.ui_requests[0]["id"], "three")

    def test_setting_survives_restart_but_is_not_a_default_for_new_chats(self):
        self.set_mode("always")
        identity = self.bridge.current["id"]
        self.bridge.close()
        self.bridge = Bridge(self.temp.name, self.events.append)
        self.assertEqual(self.bridge.current["id"], identity)
        self.assertEqual(self.bridge.current["bashApproval"], "always")
        self.assertNotIn("bashApproval", self.bridge.settings)
        self.bridge.new()
        self.assertNotIn("bashApproval", self.bridge.current)
        self.bridge.dispatch({"action": "open", "id": identity})
        self.assertEqual(self.bridge.current["bashApproval"], "always")

    def test_cancel_wins_over_always_and_does_not_save_a_grant(self):
        self.prompt()
        self.bridge.answer_ui({"id": "bash-1", "confirmed": True, "cancelled": True,
                               "alwaysAllowBash": True, "chatId": self.bridge.current["id"]})
        self.assertNotIn("bashApproval", self.bridge.current)
        self.assertEqual(self.session.sent[-1]["response"]["response"]["behavior"], "deny")

    def test_plain_allow_remains_once(self):
        self.prompt()
        self.bridge.answer_ui({"id": "bash-1", "confirmed": True})
        self.prompt("next")
        self.assertNotIn("bashApproval", self.bridge.current)
        self.assertEqual(len(self.session.sent), 1)
        self.assertEqual(self.bridge.ui_requests[0]["id"], "next")

    def test_other_tools_and_questions_cannot_enable_or_use_bash_mode(self):
        self.set_mode("always")
        for tool in ("Edit", "Write", "mcp__jarvis__computer"):
            self.prompt(tool, tool, title="Allow Bash?", description="Bash command")
            self.assertFalse(self.bridge.ui_requests[-1]["allowAlwaysBash"])
            with self.assertRaises(ValueError):
                self.bridge.answer_ui({"id": tool, "confirmed": True, "alwaysAllowBash": True,
                                       "chatId": self.bridge.current["id"]})
        self.prompt("question", "AskUserQuestion", input={"questions": [
            {"question": "Use Bash?", "options": [{"label": "Yes"}]}]})
        self.assertEqual(self.bridge.ui_requests[-1]["method"], "select")
        self.assertFalse(self.session.sent)

    def test_stale_conversation_and_invalid_mode_cannot_save_or_approve(self):
        self.prompt()
        for command in ({"mode": "all", "chatId": self.bridge.current["id"]},
                        {"mode": "always", "chatId": "other"}):
            with self.assertRaises(ValueError):
                self.bridge.set_bash_approval(command)
        with self.assertRaises(ValueError):
            self.bridge.answer_ui({"id": "bash-1", "confirmed": True, "alwaysAllowBash": True,
                                   "chatId": "other"})
        self.assertNotIn("bashApproval", self.bridge.current)
        self.assertFalse(self.session.sent)

    def test_stop_and_other_session_do_not_auto_approve(self):
        self.set_mode("always")
        self.bridge.cancelled.set()
        self.prompt("stopping")
        self.bridge.cancelled.clear()
        self.bridge.rpc_chat = "other-session"
        self.prompt("other-session")
        self.assertEqual(len(self.bridge.ui_requests), 2)
        self.assertFalse(self.session.sent)

    def test_failed_save_does_not_approve_or_enable_mode(self):
        self.prompt()
        with patch.object(self.bridge, "save", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.set_mode("always")
        self.assertEqual(self.bridge.current["bashApproval"], "ask")
        self.assertFalse(self.session.sent)

    def test_folder_change_resets_grant(self):
        self.set_mode("always")
        folder = Path(self.temp.name) / "other-folder"
        folder.mkdir()
        self.bridge.dispatch({"action": "settings", "settings": {"cwd": str(folder)}})
        self.assertNotIn("bashApproval", self.bridge.current)

    def test_generic_extension_confirmation_is_not_a_bash_approval(self):
        self.bridge.current["agent"] = "omp"
        self.bridge.current["bashApproval"] = "always"
        self.bridge.native_ui({"id": "extension", "method": "confirm", "title": "Allow Bash?",
                               "approvalKind": "bash"})
        self.assertFalse(self.bridge.ui_requests[0]["allowAlwaysBash"])
        self.assertFalse(self.session.sent)
        with self.assertRaises(ValueError):
            self.set_mode("always")

    def test_codex_shell_approvals_only_use_one_time_accept(self):
        self.bridge.current["agent"] = "codex"
        session = codex()
        session.close = lambda: None
        session.ui_callback = self.bridge.native_ui
        self.bridge.rpc = session
        self.set_mode("always")
        for method in ("item/commandExecution/requestApproval", "execCommandApproval"):
            session.server_request({"id": method, "method": method, "params": {"command": "echo fixture"}})
        self.assertEqual([e["result"]["decision"] for e in session.sent], ["accept", "approved"])
        for method, params in (
            ("item/fileChange/requestApproval", {"changes": {}}),
            ("item/permissions/requestApproval", {"permissions": {"network": True}}),
            ("mcpServer/elicitation/request", {"mode": "form", "requestedSchema": {"properties": {}}}),
            ("item/commandExecution/requestApproval", {"networkApprovalContext": {"host": "example.com", "protocol": "https"}}),
        ):
            session.server_request({"id": method + "-ask", "method": method, "params": params})
            self.assertFalse(self.bridge.ui_requests[-1]["allowAlwaysBash"])
        self.assertEqual(len(session.sent), 2)
        self.assertIn("example.com", self.bridge.ui_requests[-1]["message"])


if __name__ == "__main__":
    unittest.main()
