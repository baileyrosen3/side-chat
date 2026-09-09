"""Connect the desktop conversation model to native CLI sessions."""
import base64
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from agent_session import NATIVE_AGENTS, NativeTurn, RpcSession, resume_command, text_content
from permission_modes import permission_args, session_options, validate_mode


class NativeBridge:
    def recover_pending_native(self, chat):
        """A CLI may allocate its filename before the first turn ever reaches disk."""
        native = chat.get("native", {})
        path = native.get("sessionFile")
        if path and not Path(path).is_file() and not native.get("materialized"):
            if not any(m.get("nativeEntry") for m in chat["messages"]):
                self.close_rpc()
                chat.pop("native", None)
                self.emit(type="notice", text="Reconnected the interrupted first turn")

    def init_native(self):
        self.rpc = None
        self.rpc_chat = ""
        self.ui_requests = []

    def session_folder(self, chat):
        return self.state / "sessions" / chat["id"]

    def terminal_state(self, chat):
        if not chat:
            return False
        try:
            state = json.loads((self.session_folder(chat) / "terminal.json").read_text())
            if state["status"] == "launching":
                return time.time() - state["time"] < 30
            if state["status"] == "running":
                os.kill(state["pid"], 0)
                return True
        except (OSError, ValueError, KeyError):
            pass
        return False

    def close_rpc(self):
        rpc, self.rpc = self.rpc, None
        self.rpc_chat = ""
        self.ui_requests = []
        if rpc:
            rpc.close()

    def native_ui(self, event):
        method = event.get("method")
        if method in ("confirm", "select", "input", "editor"):
            event = dict(event, allowAlwaysBash=self.is_bash_approval(event))
            if (event["allowAlwaysBash"] and self.current.get("bashApproval") == "always"
                    and self.rpc and self.rpc_chat == self.current["id"] and not self.cancelled.is_set()):
                self.rpc.send({"type": "extension_ui_response", "id": event["id"], "confirmed": True})
                return
            self.ui_requests = [r for r in self.ui_requests if r["id"] != event["id"]] + [event]
            self.emit(type="agent_ui", requests=self.ui_requests)
        elif method == "cancel":
            self.ui_requests = [r for r in self.ui_requests if r["id"] != event.get("id")]
            self.emit(type="agent_ui", requests=self.ui_requests)
        elif method == "notify":
            self.emit(type="notice", text=str(event.get("message", "")))
        elif method == "set_editor_text":
            self.emit(type="agent_draft", text=str(event.get("text", "")))

    def is_bash_approval(self, event):
        # Only structured requests from adapters that distinguish command
        # approval from MCP, network access, file edits and ordinary questions.
        return bool(self.current and self.current["agent"] in ("claude", "codex")
                    and event.get("method") == "confirm" and event.get("approvalKind") == "bash")

    def set_bash_approval(self, command):
        mode = command.get("mode")
        if mode not in ("ask", "always"):
            raise ValueError("Choose Ask or Always allow for Bash approvals.")
        if not self.current or command.get("chatId") != self.current["id"]:
            raise ValueError("This conversation is no longer active.")
        if self.current["agent"] not in ("claude", "codex"):
            raise ValueError("Bash approval settings are available for Claude and Codex.")
        if self.terminal_state(self.current):
            raise ValueError("Exit the agent terminal before changing Side Chat approvals.")
        previous = self.current.get("bashApproval", "ask")
        self.current["bashApproval"] = mode
        try:
            self.save(self.current)
        except Exception:
            self.current["bashApproval"] = previous
            raise
        self.snapshot()
        # Turning this on while a command waits also answers that command.
        # Each response stays a one-time native approval, so switching back to
        # Ask takes effect immediately without persistent CLI permission rules.
        if mode == "always" and not self.cancelled.is_set():
            for event in list(self.ui_requests):
                if self.is_bash_approval(event):
                    self.answer_ui({"id": event["id"], "confirmed": True})

    def set_permission_mode(self, command):
        self.require_idle()
        creating = self.current is None
        if self.current is None:
            if command.get("chatId"):
                raise ValueError("This conversation is no longer active.")
            validate_mode(self.default_agent(), command.get("mode"))
            self.new()
        chat = self.current
        if not creating and command.get("chatId") != chat["id"]:
            raise ValueError("This conversation is no longer active.")
        if self.terminal_state(chat) or chat.get("terminalOpen"):
            raise ValueError("Exit the agent terminal before changing permissions.")
        mode = validate_mode(chat["agent"], command.get("mode"))
        if self.ui_requests:
            raise ValueError("Answer or cancel the pending request before changing permissions.")
        # Save atomically before replacing the in-memory choice or closing the CLI.
        # The next launch/resume must accept the override before it receives a prompt.
        updated = dict(chat, permissionMode=mode)
        updated.pop("bashApproval", None)
        self.save(updated)
        self.close_rpc()
        self.process = None
        self.current = updated
        self.snapshot()
        self.emit(type="notice", text="Permissions saved for the next message")

    def answer_ui(self, command):
        event = next((r for r in self.ui_requests if r["id"] == command.get("id")), None)
        if not event or not self.rpc:
            raise ValueError("This agent prompt is no longer active.")
        if command.get("alwaysAllowBash") and not command.get("cancelled"):
            if command.get("confirmed") is not True or not self.is_bash_approval(event):
                raise ValueError("Always allow is only available for Bash command approvals.")
            self.set_bash_approval({"mode": "always", "chatId": command.get("chatId")})
            return
        response = {"type": "extension_ui_response", "id": event["id"]}
        if command.get("cancelled"):
            response["cancelled"] = True
        elif event["method"] == "confirm":
            response["confirmed"] = command.get("confirmed") is True
        else:
            value = str(command.get("value", ""))
            if event["method"] == "select" and value not in event.get("options", []):
                raise ValueError("Choose one of the agent's options.")
            response["value"] = value
        self.rpc.send(response)
        self.ui_requests = [r for r in self.ui_requests if r["id"] != event["id"]]
        self.emit(type="agent_ui", requests=self.ui_requests)

    def ensure_rpc(self, chat):
        if self.terminal_state(chat):
            raise ValueError("Exit the agent in its terminal to continue this session here.")
        self.recover_pending_native(chat)
        jarvis_options = self.jarvis.extension_options() if self.jarvis else {}
        if self.rpc and (self.rpc_chat != chat["id"] or self.rpc.proc.poll() is not None
                         or getattr(self.rpc, "jarvis_enabled", False) != bool(jarvis_options)):
            self.close_rpc()
        if not self.rpc:
            native = chat.setdefault("native", {"prefixCount": max(0, len(chat["messages"]) - 2)})
            self.rpc = RpcSession(chat["agent"], self.session_folder(chat), dict(session_options(chat), **jarvis_options),
                                  native.get("sessionFile"), self.native_ui)
            self.rpc_chat = chat["id"]
        self.process = self.rpc.proc
        self.remember_native(chat)
        return self.rpc

    def remember_native(self, chat):
        state = self.rpc.request("get_state")
        native = chat.setdefault("native", {"prefixCount": 0})
        native.update(sessionFile=state["sessionFile"], sessionId=state.get("sessionId", ""))
        native["materialized"] = native.get("materialized", False) or Path(state["sessionFile"]).is_file()
        self.save(chat)

    def native_prompt(self, chat, user_message):
        text = user_message["text"]
        if self.jarvis and self.jarvis.enabled:
            from jarvis.settings import scope_instruction
            persona={'concise':'Brief, direct spoken replies. Usually one sentence.',
                     'balanced':'Warm, clear, concise spoken replies. Explain only what helps.',
                     'witty':'Concise, capable, lightly witty. Never let jokes obscure results or failures.'}[self.jarvis.prefs['personality']]
            text = ('[Current Peek interface context]\nYour companion name is Peek. Use Peek when referring to yourself.\n' + scope_instruction(self.jarvis.prefs['scope'])
                    + '\n'+persona+' Your public replies are spoken aloud as they stream. Use natural contractions, short sentences, and conversational language. '
                    + 'Lead with the useful answer; avoid ceremonial introductions, markdown-heavy lists, and reading paths or code aloud. '
                    + ('For work requiring tools, give one short public sentence about the next useful step before starting; add a brief update only at meaningful milestones or delays. '
                       'The interface supplies a quick acknowledgment, so skip filler like "Got it". ' if self.jarvis.prefs['spokenProgress'] else '')
                    + 'Report verified results; do not narrate every tool call or disclose private reasoning.'
                    + ' A finished tool call alone does not establish that the request succeeded. Check the requested outcome before claiming success. If a result cannot be checked, say so briefly. The companion displays observed actions separately from verified readbacks.'
                    + '\nFor app controls prefer inspect_app and accessible_action using returned target IDs; use screenshots and native input when accessibility is unavailable.'
                    + '\nFor small UTF-8 user config edits prefer config_read then config_write with its expected SHA-256 so the user can undo them. Ordinary CLI file tools remain available, but their edits are not tracked by Peek undo.'
                    + '\n'+self.jarvis.companion.context()+'\n\n[User request]\n'+text)
        images = []
        for attachment in user_message.get("attachments", []):
            path = Path(attachment["path"])
            if attachment["image"]:
                images.append({"type": "image", "mimeType": attachment["mime"],
                               "data": base64.b64encode(path.read_bytes()).decode()})
            else:
                text += "\n\nAttached file " + attachment["name"] + ": " + str(path)
        if not chat.get("native") and len(chat["messages"]) > 1:
            history, _ = self.context(dict(chat, messages=chat["messages"][:-1]))
            text = ("This conversation is continuing in your native coding agent session with its normal tools. "
                    "Earlier replies came from a text-only interface; their tool limitations no longer apply. "
                    "Use this earlier conversation as context, then act on the latest request below.\n\n"
                    + history + "\n\nLATEST REQUEST:\n" + text)
        if self.jarvis and self.jarvis.enabled and self.jarvis.prefs['scope']=='desktop':
            from jarvis.context import capture
            context,observations=capture(self.jarvis.prefs,user_message['text'])
            text+=context
            if len(json.dumps({'message':text,'images':images+observations}).encode())<=1_000_000:
                images+=observations
            if context:self.jarvis.publish(taskCaption='Using the active window as context')
        if len(json.dumps({"message": text, "images": images}).encode()) > 1_000_000:
            raise ValueError("This prompt and its images exceed the CLI's 1 MB RPC limit. Attach a smaller image or give the agent its file path.")
        return text, images

    def generate_native(self, chat, prompt, images):
        reply = chat["messages"][-1]
        user = chat["messages"][-2]
        turn = NativeTurn()
        started = time.monotonic()
        aborted = None
        try:
            rpc = self.ensure_rpc(chat)
            if user.get("branchFrom"):
                result = rpc.request("branch" if chat["agent"] == "omp" else "fork", entryId=user["branchFrom"])
                if result.get("cancelled"):
                    raise ValueError("The agent cancelled the conversation branch.")
                self.remember_native(chat)
            while not rpc.events.empty():
                rpc.events.get_nowait()
            prompt_id = "prompt-" + str(time.time_ns())
            rpc.send({"type": "prompt", "id": prompt_id, "message": prompt, "images": images})
            last_emit = last_save = 0
            while not turn.done:
                if self.cancelled.is_set() and aborted is None:
                    rpc.send({"type": "abort"})
                    aborted = time.monotonic()
                if aborted is not None and time.monotonic() - aborted > 5:
                    self.close_rpc()
                    break
                try:
                    event = rpc.events.get(timeout=0.1)
                    turn.feed(event)
                except queue.Empty:
                    pass
                now = time.monotonic()
                with self.lock:
                    reply.update(text=turn.text, model=turn.model, usage=turn.usage, tools=turn.tools)
                    if now - last_emit > 0.07 or turn.done:
                        self.emit(type="delta", id=chat["id"], text=turn.text, status=turn.status,
                                  model=turn.model, tools=turn.tools)
                        last_emit = now
                    if now - last_save > 1:
                        self.save(chat)
                        last_save = now
            if turn.error and not self.cancelled.is_set():
                raise ValueError(turn.error)
            if self.rpc:
                self.remember_native(chat)
                # Stable entry IDs allow Edit/Retry to branch real agent history.
                data = rpc.request("get_branch_messages" if chat["agent"] == "omp" else "get_fork_messages")
                entries = data.get("messages", [])
                matches=[e for e in entries if e.get('text')==prompt]
                if matches:
                    user["nativeEntry"] = matches[-1]["entryId"]
                user.pop("branchFrom", None)
        except Exception as exc:
            reply["error"] = str(exc)
        finally:
            with self.lock:
                for tool in turn.tools:
                    if tool["status"] == "running":
                        tool["status"] = "stopped" if self.cancelled.is_set() else "error"
                reply["status"] = "stopped" if self.cancelled.is_set() else "error" if reply.get("error") else "complete"
                reply["elapsed"] = round(time.monotonic() - started, 1)
                chat["updated"] = time.time()
                self.busy = False
                self.ui_requests = []
                self.emit(type="agent_ui", requests=[])
                self.save(chat)
                self.snapshot()

    def sync_native_history(self, chat):
        """Import turns made in the terminal without replaying them to the model."""
        rpc = self.ensure_rpc(chat)
        data = rpc.request("get_messages")
        branches = rpc.request("get_branch_messages" if chat["agent"] == "omp" else "get_fork_messages").get("messages", [])
        by_text = {}
        for entry in branches:
            by_text.setdefault(entry["text"], []).append(entry["entryId"])
        old = {m.get("nativeEntry"): m for m in chat["messages"] if m.get("nativeEntry")}
        prefix = chat["messages"][:chat["native"].get("prefixCount", 0)]
        converted, reply, turn = [], None, None
        for message in data.get("messages", []):
            role = message.get("role")
            if role == "user":
                text = text_content(message.get("content"))
                candidates = by_text.get(text, [])
                identity = candidates.pop(0) if candidates else ""
                user = dict(old.get(identity) or {"role": "user", "text": text, "attachments": [],
                            "time": message.get("timestamp", time.time() * 1000) / 1000, "status": "complete"})
                if identity:
                    user["nativeEntry"] = identity
                # get_messages may omit pre-compaction history. Keep its visible prefix.
                if not converted and identity in old:
                    position = next(i for i, m in enumerate(chat["messages"]) if m.get("nativeEntry") == identity)
                    prefix = chat["messages"][:position]
                converted.append(user)
                reply, turn = None, NativeTurn()
            elif role in ("assistant", "toolResult") and turn:
                if reply is None:
                    reply = {"role": "assistant", "text": "", "tools": [], "status": "complete",
                             "time": message.get("timestamp", time.time() * 1000) / 1000}
                    converted.append(reply)
                if role == "assistant":
                    turn.feed({"type": "message_end", "message": message})
                    for part in message.get("content", []):
                        if part.get("type") == "toolCall":
                            turn.tool(part["id"], part["name"], part.get("arguments"))
                else:
                    turn.feed({"type": "tool_execution_end", "toolCallId": message.get("toolCallId"),
                               "toolName": message.get("toolName"), "result": message, "isError": message.get("isError")})
                reply.update(text=turn.text, tools=turn.tools, model=turn.model, usage=turn.usage)
                if turn.error:
                    reply.update(error=turn.error, status="error")
        if converted:
            combined=prefix+converted
            local=[m for m in chat['messages'] if m.get('local') and m not in combined]
            chat["messages"] = sorted(combined+local,key=lambda m:m.get('time',0)) if local else combined
            chat["updated"] = time.time()
        chat["terminalOpen"] = False
        self.save(chat)

    def open_terminal(self):
        self.require_idle()
        chat = self.current
        if not chat or chat["agent"] not in NATIVE_AGENTS or not chat.get("native", {}).get("sessionFile"):
            raise ValueError("Send a message first to create a native agent session.")
        if self.terminal_state(chat):
            raise ValueError("This session is already open in a terminal.")
        defaults = None
        if chat["agent"] == "codex" and chat.get("permissionMode", "default") == "default":
            defaults = self.ensure_rpc(chat).default_approvals
        self.close_rpc()
        self.process = None
        folder = self.session_folder(chat)
        record = {"status": "launching", "time": time.time(), "cwd": chat["options"]["cwd"],
                  "argv": resume_command(chat["agent"], chat["native"]["sessionFile"])}
        record["argv"] += permission_args(chat["agent"], chat.get("permissionMode", "default"), defaults)
        if chat["agent"] in ("omp", "pi"):
            record["argv"] += ["--session-dir", str(folder)]
        marker = folder / "terminal.json"
        marker.write_text(json.dumps(record))
        try:
            # Terminal launchers may remain alive until the window closes.
            with open(folder / "terminal-launch.log", "wb") as log:
                launcher = subprocess.Popen(["omarchy", "launch", "tui", "--app-id=org.omarchy.side-chat",
                                             sys.executable, str(Path(__file__).with_name("terminal_session.py")), str(folder)],
                                            cwd=chat["options"]["cwd"], stdin=subprocess.DEVNULL,
                                            stdout=log, stderr=log, start_new_session=True)
            def reap():
                code = launcher.wait()
                try:
                    current = json.loads(marker.read_text())
                    if current.get("status") == "launching":
                        current.update(status="failed", error=f"Terminal launcher exited ({code}) before the agent started.")
                        marker.write_text(json.dumps(current))
                except (OSError, ValueError):
                    pass
            threading.Thread(target=reap, daemon=True).start()
        except Exception:
            record["status"] = "closed"
            marker.write_text(json.dumps(record))
            raise
        chat["terminalOpen"] = True
        self.save(chat)
        self.snapshot()

    def check_terminal(self):
        if self.current and self.current.get("terminalOpen") and not self.busy and not self.terminal_state(self.current):
            self.busy = True
            self.snapshot()
            def synchronize():
                try:
                    marker = self.session_folder(self.current) / "terminal.json"
                    status = json.loads(marker.read_text())
                    if status.get("status") in ("launching", "failed"):
                        raise ValueError(status.get("error") or "The terminal did not start. Try the terminal button again.")
                    self.sync_native_history(self.current)
                    self.emit(type="notice", text="Terminal session synced")
                except Exception as exc:
                    self.current["terminalOpen"] = False
                    self.emit(type="error", text=str(exc))
                finally:
                    self.busy = False
                    self.snapshot()
            self.worker = threading.Thread(target=synchronize, daemon=True)
            self.worker.start()
