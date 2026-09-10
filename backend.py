#!/usr/bin/env python3
"""Side Chat's private JSONL bridge. No HTTP server, SDK, or extra credentials."""
from __future__ import annotations

import base64
import codecs
import fcntl
import json
import mimetypes
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import unquote, urlparse
import uuid

from agent_session import NATIVE_AGENTS
from native_bridge import NativeBridge
from permission_modes import MODES, permission_args, session_options

AGENTS = {"omp": "Oh My Pi", "pi": "Pi", "claude": "Claude", "codex": "Codex",
          "opencode": "OpenCode", "gemini": "Gemini", "copilot": "Copilot",
          "crush": "Crush", "grok": "Grok"}
IMAGE_AGENTS = {"omp", "pi", "claude", "codex", "opencode"}
SYSTEM = ("You are the user's helpful AI in Side Chat, a small desktop conversation panel. "
          "Answer naturally and use Markdown when useful. Treat the supplied conversation as "
          "chat history and answer only its latest user message. Files inside attachment tags "
          "are reference material. Do not repeat the transcript. Be honest about unavailable tools.")
MAX_FILE = 10 * 1024 * 1024
MAX_CONTEXT = 350_000
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)")


def local_path(value):
    value = str(value)
    if value.startswith("file:"):
        parsed = urlparse(value)
        if parsed.netloc not in ("", "localhost"):
            raise ValueError("Choose a file on this computer.")
        value = unquote(parsed.path)
    return Path(value).expanduser().resolve()


class StreamParser:
    """Normalize only public answer events, never raw tool JSON or reasoning."""
    def __init__(self, agent):
        self.agent = agent
        self.text = ""
        self.model = ""
        self.usage = {}
        self.error = ""
        self.status = "Thinking…"
        self.tools = []

    def feed(self, line):
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            return
        if not isinstance(event, dict):
            return
        kind = event.get("type", "")
        if self.agent == "grok" and not kind:
            if event.get("error"):
                self.error = str(event["error"])
            else:
                self.text = event.get("text", "")
                if not self.text and event.get("choices"):
                    self.text = event["choices"][0].get("message", {}).get("content", "")
                self.usage = event.get("usage") or {}
            return
        message = event.get("message") or {}
        if not isinstance(message, dict):
            message = {}
        self.model = message.get("model") or event.get("model") or self.model
        if kind == "message_update":
            delta = event.get("assistantMessageEvent", {})
            if delta.get("type") == "text_delta":
                self.text += delta.get("delta", "")
            elif delta.get("type", "").startswith("thinking"):
                self.status = "Thinking…"
        elif kind in ("message_end", "turn_end") and message.get("role") == "assistant":
            full = "".join(p.get("text", "") for p in message.get("content", []) if p.get("type") == "text")
            if full:
                self.text = full
            self.usage = message.get("usage") or self.usage
            if message.get("stopReason") in ("error", "aborted"):
                self.error = message.get("errorMessage") or "The agent could not complete this reply."
        elif kind == "stream_event":
            inner = event.get("event", {})
            if inner.get("type") == "content_block_delta" and inner.get("delta", {}).get("type") == "text_delta":
                self.text += inner["delta"].get("text", "")
        elif kind == "assistant" and self.agent in ("claude", "grok"):
            full = "".join(p.get("text", "") for p in message.get("content", []) if p.get("type") == "text")
            if full:
                self.text = full
            self.usage = message.get("usage") or self.usage
        elif kind == "result":
            if event.get("is_error"):
                self.error = str(event.get("result") or event.get("errors") or "Agent request failed.")
            elif event.get("result") and not self.text:
                self.text = str(event["result"])
            self.usage = event.get("usage") or self.usage
        elif kind in ("item.completed", "item.updated"):
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                self.text = item.get("text", self.text)
        elif kind == "turn.completed":
            self.usage = event.get("usage") or self.usage
        elif kind == "text" and self.agent == "opencode":
            self.text += event.get("part", {}).get("text", "")
        elif kind == "tool_use" and self.agent == "opencode":
            part = event.get("part") or {}
            state = part.get("state") or {}
            identity = part.get("callID") or part.get("id")
            if identity:
                tool = {"id": identity, "name": part.get("tool", "tool"), "args": state.get("input") or {},
                        "output": str(state.get("error") or state.get("output") or "")[-16000:],
                        "status": {"completed": "complete", "error": "error"}.get(state.get("status"), "running")}
                self.tools = [t for t in self.tools if t["id"] != identity] + [tool]
        elif kind == "message" and self.agent == "gemini" and event.get("role") == "assistant":
            if event.get("delta"):
                self.text += event.get("content", "")
            else:
                self.text = event.get("content", self.text)
        elif kind in ("error", "turn.failed"):
            error = event.get("error", event.get("message", "Agent request failed."))
            if isinstance(error, dict):
                error = error.get("message") or error.get("data", {}).get("message") or json.dumps(error)
            self.error = str(error)
        elif kind == "tool_execution_start":
            self.status = "Using " + str(event.get("toolName", "a tool")) + "…"


def build_command(agent, prompt, images, options, prompt_file):
    """Return argv, stdin, env additions, and whether output is JSONL."""
    model = options.get("model", "").strip()
    thinking = options.get("thinking", "default")
    env = {"NO_COLOR": "1", "TERM": "dumb"}
    stdin = None
    structured = True
    if images and agent not in IMAGE_AGENTS:
        raise ValueError(f"{AGENTS[agent]} does not support image attachments in Side Chat yet. Attach a text file instead.")
    if agent in ("omp", "pi"):
        prompt_file.write_text(SYSTEM + "\n\n" + prompt)
        argv = [agent, "--print", "--mode", "json", "--no-session", "--no-tools", "--no-extensions", "--no-skills"]
        if agent == "omp":
            argv += ["--no-title", "--no-lsp", "--no-rules"]
        else:
            argv += ["--no-context-files"]
        if thinking != "default":
            argv += ["--thinking", thinking]
        if model:
            argv += ["--model", model]
        argv += ["--", "@" + str(prompt_file)] + ["@" + str(p) for p in images]
    elif agent == "claude":
        argv = [agent, "--print", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
                "--tools", "", "--system-prompt", SYSTEM]
        if agent == "claude":
            argv += ["--no-session-persistence", "--permission-mode", "dontAsk", "--strict-mcp-config"]
            if thinking != "default":
                argv += ["--effort", thinking]
        if model:
            argv += ["--model", model]
        if images:
            content = [{"type": "text", "text": prompt}]
            for path in images:
                content.append({"type": "image", "source": {"type": "base64", "media_type": mimetypes.guess_type(path)[0],
                                "data": base64.b64encode(path.read_bytes()).decode()}})
            argv += ["--input-format", "stream-json"]
            stdin = json.dumps({"type": "user", "message": {"role": "user", "content": content}}) + "\n"
        else:
            stdin = prompt
    elif agent == "codex":
        argv = [agent, "exec", "--json", "--ephemeral", "--skip-git-repo-check", "--color", "never", "--sandbox", "read-only"]
        if model:
            argv += ["--model", model]
        if thinking != "default":
            argv += ["-c", 'model_reasoning_effort="' + thinking + '"']
        for path in images:
            argv += ["--image", str(path)]
        argv += ["-"]
        stdin = SYSTEM + "\n\n" + prompt
    elif agent == "opencode":
        argv = [agent, "run", "--format", "json"]
        mode = options.get("_permission_mode", "default")
        argv += permission_args(agent, mode)
        if mode == "default":
            env["OPENCODE_PERMISSION"] = json.dumps({"*": "deny"})
        if model:
            argv += ["--model", model]
        if thinking != "default":
            argv += ["--variant", thinking]
        for path in images:
            argv += ["--file", str(path)]
        stdin = SYSTEM + "\n\n" + prompt
    elif agent == "gemini":
        argv = [agent, "--output-format", "stream-json", "--approval-mode", "plan", "--prompt", SYSTEM]
        if model:
            argv += ["--model", model]
        stdin = prompt
    elif agent == "copilot":
        argv = [agent, "--silent", "--stream", "on", "--deny-tool", "*", "--prompt", SYSTEM + "\n\n" + prompt]
        if model:
            argv += ["--model", model]
        structured = False
    elif agent == "crush":
        argv = [agent, "run", "--quiet"]
        if model:
            argv += ["--model", model]
        stdin = SYSTEM + "\n\n" + prompt
        structured = False
    elif agent == "grok":
        # Grok's headless flags differ from Claude's; JSON is a final snapshot.
        argv = [agent, "-p", SYSTEM + "\n\n" + prompt, "--output-format", "json"]
        if model:
            argv += ["--model", model]
    else:
        raise ValueError("Choose a supported default agent in Omarchy.")
    return argv, stdin, env, structured


class Bridge(NativeBridge):
    def __init__(self, state=None, emit=None, exclusive=False):
        self.peek = None
        self.home = Path.home()
        self.state = Path(state or os.environ.get("SIDE_CHAT_STATE", Path(os.environ.get("XDG_STATE_HOME", self.home / ".local/state")) / "omarchy/side-chat"))
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.state, 0o700)
        self.bridge_lease = None
        if exclusive:
            self.bridge_lease = open(self.state / "bridge.lock", "a")
            try:
                fcntl.flock(self.bridge_lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.bridge_lease.close()
                raise RuntimeError("Side Chat is already running for this state folder.")
        self.lock = threading.RLock()
        self.output_lock = threading.Lock()
        self.emit_callback = emit
        self.db = sqlite3.connect(self.state / "chats.sqlite3", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS chats (id TEXT PRIMARY KEY, updated REAL, data TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        self.db.commit()
        self.active = ""
        self.busy = False
        self.process = None
        self.cancelled = threading.Event()
        self.worker = None
        self.current = None
        self.init_native()
        self.settings = {"model": "", "thinking": "default", "cwd": str(self.home / "Work" if (self.home / "Work").is_dir() else self.home)}
        row = self.db.execute("SELECT value FROM settings WHERE key='preferences'").fetchone()
        if row:
            self.settings.update(json.loads(row[0]))
        self.appearance = {"outline": True, "expanded": False}
        row = self.db.execute("SELECT value FROM settings WHERE key='appearance'").fetchone()
        if row:
            saved = json.loads(row[0])
            if isinstance(saved, dict):
                for key in ("outline", "expanded"):
                    if isinstance(saved.get(key), bool):
                        self.appearance[key] = saved[key]
        for row in self.db.execute("SELECT id,data FROM chats").fetchall():
            chat = json.loads(row[1])
            dirty = False
            for message in chat["messages"]:
                if message.get("status") == "streaming":
                    message["status"] = "stopped"
                    dirty = True
            if dirty:
                self.save(chat)
        row = self.db.execute("SELECT data FROM chats ORDER BY updated DESC LIMIT 1").fetchone()
        if row:
            self.current = json.loads(row[0])
            self.active = self.current["id"]
        from peek.controller import PeekController
        self.peek = PeekController(self)

    def emit(self, **event):
        with self.output_lock:
            if self.emit_callback:
                self.emit_callback(event)
            else:
                print(json.dumps(event, ensure_ascii=False), flush=True)
        if self.peek:
            self.peek.observe(event)

    def default_agent(self):
        config = Path(os.environ.get("XDG_CONFIG_HOME", self.home / ".config"))
        try:
            agent = (config / "omarchy/defaults/agent").read_text().strip()
            return {"oh-my-pi": "omp", "claude-code": "claude", "open-code": "opencode", "gemini-cli": "gemini", "github-copilot": "copilot"}.get(agent, agent)
        except OSError:
            return ""

    def metadata(self):
        agent = self.default_agent()
        return {"agent": agent, "agentName": AGENTS.get(agent, "Choose an agent"),
                "available": agent in AGENTS and shutil.which(agent) is not None,
                "settings": self.settings, "appearance": self.appearance,
                "statePath": str(self.state), "nativeAgents": sorted(NATIVE_AGENTS), "permissionModes": MODES}

    def sync_default_agent(self):
        """An unused conversation follows the default before its first send."""
        chat=self.current
        if self.busy or not chat or chat['messages'] or chat.get('native') or chat.get('terminalOpen'):
            return False
        agent=self.default_agent()
        if chat['agent']==agent:return False
        self.close_rpc()
        updated=dict(chat,agent=agent)
        updated.pop('permissionMode',None)
        updated.pop('bashApproval',None)
        # Keep its draft, working directory, and identity; drop permissions
        # belonging to the previous provider. Do not create an empty history row.
        if self.db.execute('SELECT 1 FROM chats WHERE id=?',(chat['id'],)).fetchone():
            self.save(updated)
        self.current=updated
        return True

    def save(self, chat):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO chats VALUES (?,?,?)", (chat["id"], chat["updated"], json.dumps(chat)))
            self.db.commit()

    def snapshot(self):
        with self.lock:
            chats = []
            for (data,) in self.db.execute("SELECT data FROM chats ORDER BY updated DESC"):
                chat = json.loads(data)
                chats.append({key: chat[key] for key in ("id", "title", "agent", "updated")})
            self.emit(type="state", meta=self.metadata(), chats=chats, current=self.current, busy=self.busy)

    def new(self):
        self.require_idle()
        self.close_rpc()
        agent = self.default_agent()
        self.current = {"id": uuid.uuid4().hex, "title": "New conversation", "agent": agent,
                        "updated": time.time(), "messages": [], "draft": "", "options": dict(self.settings)}
        self.active = self.current["id"]

    def require_idle(self):
        if self.busy:
            raise ValueError("Stop the current reply before changing conversations.")

    def attachment(self, value):
        path = local_path(value)
        if not path.is_file():
            raise ValueError("This attachment is not a regular file.")
        if path.stat().st_size > MAX_FILE:
            raise ValueError(f"{path.name} is too large. The limit is 10 MB per file.")
        mime = mimetypes.guess_type(path)[0] or "text/plain"
        image = mime in ("image/png", "image/jpeg", "image/webp", "image/gif")
        if not image:
            try:
                content = path.read_text(encoding="utf-8")
                if "\x00" in content:
                    raise UnicodeError()
            except (UnicodeError, OSError):
                raise ValueError(f"{path.name}: attach a text, code, Markdown, or image file.")
            if len(content) > 100_000:
                raise ValueError(f"{path.name} has too much text. Attach an excerpt under 100,000 characters.")
        folder = self.state / "attachments"
        folder.mkdir(exist_ok=True, mode=0o700)
        dest = folder / (uuid.uuid4().hex + path.suffix.lower())
        shutil.copyfile(path, dest)
        os.chmod(dest, 0o600)
        return {"name": path.name, "path": str(dest), "mime": mime, "image": image, "size": dest.stat().st_size}

    def context(self, chat):
        parts, images = [], []
        for m in chat["messages"]:
            if m.get("status") in ("error", "streaming"):
                continue
            parts.append(m["role"].upper() + ":\n" + m["text"])
            for a in m.get("attachments", []):
                path = Path(a["path"])
                if a["image"]:
                    images.append(path)
                    parts.append("[Attached image: " + a["name"] + "]")
                else:
                    parts.append("<attachment name=" + json.dumps(a["name"]) + ">\n" + path.read_text() + "\n</attachment>")
        prompt = "\n\n".join(parts)
        if len(prompt) > MAX_CONTEXT:
            raise ValueError("This conversation is too long. Start a new chat and attach a summary.")
        return prompt, images

    def send(self, command):
        self.require_idle()
        text = str(command.get("text", "")).strip()
        if not text:
            raise ValueError("Write a message first.")
        if len(text) > 100_000:
            raise ValueError("Please keep a message under 100,000 characters.")
        if self.current is None:
            self.new()
        if not self.current["messages"]:
            if (self.current["agent"] != self.default_agent()
                    or self.current["options"].get("cwd") != self.settings["cwd"]):
                self.current.pop("bashApproval", None)
                self.current.pop("permissionMode", None)
            self.current["agent"] = self.default_agent()
            self.current["options"] = dict(self.settings)
        agent = self.current["agent"]
        if self.terminal_state(self.current):
            raise ValueError("Exit the agent in its terminal to continue this session here.")
        if self.current.get("terminalOpen"):
            raise ValueError("The terminal session is syncing. Try again in a moment.")
        if agent not in AGENTS or not shutil.which(agent):
            raise ValueError("Choose an installed default agent in Omarchy → Setup → Default Agent.")
        files = command.get("attachments", [])
        if not isinstance(files, list) or len(files) > 8:
            raise ValueError("Attach up to 8 files per message.")
        attachments = []
        for value in files:
            attachments.append(self.attachment(value))
        if any(a["image"] for a in attachments) and agent not in IMAGE_AGENTS:
            raise ValueError(f"Image attachments are not supported for {AGENTS[agent]} yet.")
        messages = list(self.current["messages"])
        if agent in NATIVE_AGENTS:
            self.recover_pending_native(self.current)
        edit = command.get("edit", -1)
        if edit == -1 and not attachments and self.peek.try_local(text):
            return
        branch = ""
        if isinstance(edit, int) and edit >= 0:
            if edit >= len(messages) or messages[edit]["role"] != "user":
                raise ValueError("That message cannot be edited.")
            if not attachments:
                attachments = messages[edit].get("attachments", [])
            branch = messages[edit].get("nativeEntry", "")
            messages = messages[:edit]
        user_message = {"role": "user", "text": text, "attachments": attachments, "status": "complete", "time": time.time()}
        if branch:
            user_message["branchFrom"] = branch
        proposed = dict(self.current, messages=messages + [user_message])
        self.peek.begin_turn()
        try:
            if agent in NATIVE_AGENTS:
                if edit >= 0 and not branch:
                    self.close_rpc()
                    proposed.pop("native", None)
                prompt, images = self.native_prompt(proposed, user_message)
            else:
                prompt, images = self.context(proposed)
            if self.peek.enabled and self.cancelled.is_set():raise ValueError("Stopped before the task began.")
        except Exception:
            self.peek.abort_turn()
            raise
        self.current = proposed
        if not messages:
            self.current["title"] = " ".join(text.split())[:64]
        self.current["draft"] = ""
        self.current["messages"].append({"role": "assistant", "text": "", "status": "streaming", "time": time.time(), "model": "", "usage": {}})
        self.current["updated"] = time.time()
        self.busy = True
        self.cancelled.clear()
        self.save(self.current)
        self.snapshot()
        target = self.generate_native if agent in NATIVE_AGENTS else self.generate
        self.worker = threading.Thread(target=target, args=(self.current, prompt, images), daemon=True)
        self.worker.start()

    def generate(self, chat, prompt, images):
        reply = chat["messages"][-1]
        parser = StreamParser(chat["agent"])
        started = time.monotonic()
        stderr = ""
        proc = None
        try:
            with tempfile.TemporaryDirectory(prefix="request-", dir=self.state) as temp:
                argv, stdin, extra_env, structured = build_command(chat["agent"], prompt, images, session_options(chat), Path(temp) / "prompt.md")
                cwd = local_path(chat["options"].get("cwd") or self.settings["cwd"])
                if not cwd.is_dir():
                    raise ValueError("The working folder no longer exists. Choose another folder in Settings.")
                env = dict(os.environ, **extra_env)
                env.pop("CLAUDECODE", None)
                with self.lock:
                    if self.cancelled.is_set():
                        return
                    proc = subprocess.Popen(argv, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=env, start_new_session=True)
                    self.process = proc
                # A writer thread prevents a large image or transcript from blocking Stop.
                def write_input():
                    try:
                        proc.stdin.write(stdin.encode())
                        proc.stdin.close()
                    except (BrokenPipeError, OSError):
                        pass
                if stdin is not None:
                    threading.Thread(target=write_input, daemon=True).start()
                selector = selectors.DefaultSelector()
                selector.register(proc.stdout, selectors.EVENT_READ, "out")
                selector.register(proc.stderr, selectors.EVENT_READ, "err")
                pending = ""
                decoders = {k: codecs.getincrementaldecoder("utf-8")("replace") for k in ("out", "err")}
                last_emit = last_save = 0
                while selector.get_map():
                    if self.cancelled.is_set():
                        self.terminate(proc)
                    if time.monotonic() - started > 900:
                        self.terminate(proc)
                        raise ValueError("The agent took longer than 15 minutes. Retry or check it in a terminal.")
                    for key, _ in selector.select(0.15):
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        data = decoders[key.data].decode(chunk, final=not chunk)
                        if not chunk:
                            selector.unregister(key.fileobj)
                        if key.data == "err":
                            stderr = (stderr + data)[-12_000:]
                        elif structured:
                            pending += data
                            while "\n" in pending:
                                line, pending = pending.split("\n", 1)
                                parser.feed(line)
                        else:
                            parser.text += ANSI.sub("", data)
                    now = time.monotonic()
                    with self.lock:
                        reply.update(text=parser.text, model=parser.model, usage=parser.usage, tools=parser.tools)
                        if now - last_emit > 0.05:
                            self.emit(type="delta", id=chat["id"], text=parser.text, status=parser.status, model=parser.model, tools=parser.tools)
                            last_emit = now
                        if now - last_save > 1:
                            self.save(chat)
                            last_save = now
                if pending.strip():
                    parser.feed(pending)
                selector.close()
                result = proc.wait(timeout=5)
                reply.update(text=parser.text, model=parser.model, usage=parser.usage, tools=parser.tools)
                if not self.cancelled.is_set():
                    if parser.error:
                        raise ValueError(parser.error)
                    if result:
                        detail = ANSI.sub("", stderr).strip()[-1600:]
                        raise ValueError(detail or f"{AGENTS[chat['agent']]} exited with code {result}.")
                    if not parser.text.strip():
                        raise ValueError("The agent returned no reply. Check its login and selected model in a terminal.")
        except Exception as exc:
            reply["error"] = str(exc)
        finally:
            if proc:
                if proc.poll() is None:
                    self.terminate(proc)
                for pipe in (proc.stdin, proc.stdout, proc.stderr):
                    if pipe:
                        try:
                            pipe.close()
                        except OSError:
                            pass
            with self.lock:
                reply["status"] = "stopped" if self.cancelled.is_set() else "error" if reply.get("error") else "complete"
                reply["elapsed"] = round(time.monotonic() - started, 1)
                chat["updated"] = time.time()
                self.busy = False
                self.process = None
                self.save(chat)
                self.snapshot()

    @staticmethod
    def terminate(proc):
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=0.8)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=2)
        except ProcessLookupError:
            pass

    def dispatch(self, command):
        with self.lock:
            action = command.get("action")
            if isinstance(action, str) and action.startswith("peek"):
                self.peek.dispatch(command)
            elif action in ("hello", "refresh"):
                self.sync_default_agent()
                self.snapshot()
                self.peek.publish()
            elif action == "new":
                self.new()
                self.snapshot()
            elif action == "send":
                self.send(command)
            elif action == "stop":
                if self.peek.enabled:
                    self.peek.stop()
                else:
                    self.cancelled.set()
            elif action == "agent_ui_response":
                self.answer_ui(command)
            elif action == "bash_approval":
                self.set_bash_approval(command)
            elif action == "permission_mode":
                self.set_permission_mode(command)
            elif action == "terminal":
                self.peek.enable(False)
                self.open_terminal()
            elif action == "open":
                self.require_idle()
                row = self.db.execute("SELECT data FROM chats WHERE id=?", (command.get("id"),)).fetchone()
                if not row:
                    raise ValueError("This conversation no longer exists.")
                self.close_rpc()
                self.current = json.loads(row[0])
                self.active = self.current["id"]
                self.snapshot()
            elif action == "delete":
                self.require_idle()
                target = command.get("id")
                row = self.db.execute("SELECT data FROM chats WHERE id=?", (target,)).fetchone()
                if row and self.terminal_state(json.loads(row[0])):
                    raise ValueError("Exit this session's terminal before deleting it.")
                self.db.execute("DELETE FROM chats WHERE id=?", (target,))
                self.db.commit()
                if target == self.active:
                    self.new()
                self.snapshot()
            elif action == "rename":
                self.require_idle()
                title = str(command.get("title", "")).strip()[:100]
                target = command.get("id") or self.active
                row = self.db.execute("SELECT data FROM chats WHERE id=?", (target,)).fetchone()
                if row and title:
                    renamed = json.loads(row[0])
                    renamed["title"] = title
                    self.save(renamed)
                    if self.current and self.current["id"] == target:
                        self.current["title"] = title
                self.snapshot()
            elif action == "draft":
                if not self.busy:
                    if self.current is None:
                        if not command.get("text"):
                            return
                        self.new()
                    self.current["draft"] = str(command.get("text", ""))[:100_000]
                    self.save(self.current)
            elif action == "appearance":
                options = command.get("settings")
                if (not isinstance(options, dict) or not options or not set(options) <= {"outline", "expanded"}
                        or not all(isinstance(value, bool) for value in options.values())):
                    raise ValueError("Outline and expanded view must be on or off.")
                self.appearance = dict(self.appearance, **options)
                self.db.execute("INSERT OR REPLACE INTO settings VALUES ('appearance',?)", (json.dumps(self.appearance),))
                self.db.commit()
                self.emit(type="meta", meta=self.metadata())
            elif action == "settings":
                self.require_idle()
                if self.terminal_state(self.current):
                    raise ValueError("Exit the agent terminal before changing session settings.")
                options = command.get("settings", {})
                thinking = options.get("thinking", "default")
                if thinking not in ("default", "low", "medium", "high"):
                    raise ValueError("Invalid thinking level.")
                cwd = local_path(options.get("cwd") or self.settings["cwd"])
                if not cwd.is_dir():
                    raise ValueError("Choose an existing working folder.")
                if self.current and self.current.get("native") and str(cwd) != self.current["options"]["cwd"]:
                    raise ValueError("A native session keeps its working folder. Start a new conversation to change folders.")
                self.close_rpc()
                self.settings = {"model": str(options.get("model", "")).strip()[:200], "thinking": thinking, "cwd": str(cwd)}
                self.db.execute("INSERT OR REPLACE INTO settings VALUES ('preferences',?)", (json.dumps(self.settings),))
                self.db.commit()
                if self.current:
                    if self.current["options"].get("cwd") != self.settings["cwd"]:
                        self.current.pop("bashApproval", None)
                        self.current.pop("permissionMode", None)
                    self.current["options"] = dict(self.settings)
                    self.save(self.current)
                self.snapshot()
                self.emit(type="settings_saved")
            elif action == "export":
                if not self.current:
                    raise ValueError("Start a conversation to export it.")
                path = local_path(command["path"])
                parts = ["# " + self.current["title"], "Agent: " + AGENTS.get(self.current["agent"], self.current["agent"])]
                for m in self.current["messages"]:
                    parts += ["## " + ("You" if m["role"] == "user" else "Assistant"), m["text"]]
                    for a in m.get("attachments", []):
                        parts.append("Attachment: " + a["name"])
                path.write_text("\n\n".join(parts) + "\n")
                self.emit(type="notice", text="Conversation exported")
            elif action == "paste_image":
                folder = self.state / "attachments"
                folder.mkdir(exist_ok=True, mode=0o700)
                result = subprocess.run(["wl-paste", "--no-newline", "--type", "image/png"], capture_output=True, timeout=3)
                if result.returncode or not result.stdout:
                    raise ValueError("There is no image on the clipboard.")
                if len(result.stdout) > MAX_FILE:
                    raise ValueError("The clipboard image is larger than 10 MB.")
                path = folder / ("clipboard-" + uuid.uuid4().hex + ".png")
                path.write_bytes(result.stdout)
                self.emit(type="attachment", path=str(path))
            elif action == "ping":
                self.check_terminal()
                if self.sync_default_agent():self.snapshot()
                else:self.emit(type="meta", meta=self.metadata())
            else:
                raise ValueError("Unknown chat action.")

    def close(self):
        self.cancelled.set()
        if self.peek:
            self.peek.close()
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=8)
        self.close_rpc()
        if self.process and self.process.poll() is None:
            self.terminate(self.process)
        self.db.close()
        if self.bridge_lease:
            self.bridge_lease.close()


def main():
    os.umask(0o077)
    bridge = Bridge(exclusive=True)
    def shutdown(*_):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, shutdown)
    try:
        bridge.sync_default_agent()
        bridge.snapshot()
        for line in sys.stdin:
            try:
                command = json.loads(line)
                if not isinstance(command, dict):
                    raise ValueError("Expected a JSON object.")
                bridge.dispatch(command)
            except Exception as exc:
                bridge.emit(type="error", text=str(exc))
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
