# SPDX-License-Identifier: GPL-3.0-or-later
"""Small file-backed bridge to the user's Voxtype daemon.

Voxtype owns microphone capture and ASR in this mode.  Peek asks the daemon to
write one transcript to a private file, then reads that file after recording
finishes.  Keeping the bridge file-backed avoids depending on Voxtype's
internal IPC protocol while still allowing Peek to preserve its own input,
agent, and speech queues.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading


class VoxtypeError(RuntimeError):
    """A user-actionable Voxtype integration failure."""


class VoxtypeBridge:
    def __init__(self, directory):
        self.binary = shutil.which("voxtype")
        if not self.binary:
            raise VoxtypeError("Voxtype is not installed. Install voxtype-bin or choose a bundled Peek speech model.")
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        self.lock = threading.RLock()
        self.path = None
        self.active = False
        self.sequence = 0

    def _run(self, args, timeout, allowed=(0,)):
        try:
            result = subprocess.run([self.binary, *args], capture_output=True, text=True,
                                    timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise VoxtypeError(f"Could not contact Voxtype: {exc}") from exc
        if result.returncode not in allowed:
            detail = (result.stderr or result.stdout).strip()
            raise VoxtypeError(detail or f"Voxtype exited with status {result.returncode}.")
        return result

    def start(self):
        with self.lock:
            if self.active:
                return
            self.sequence += 1
            self.path = self.directory / f"transcript-{os.getpid()}-{self.sequence}.txt"
            self.path.unlink(missing_ok=True)
            # File mode is explicit so Peek never types into whichever app is
            # currently focused.  Peek owns the submit step after reading it.
            self._run(["record", "start", f"--file={self.path}", "--no-osd", "--no-auto-submit"], 10)
            self.active = True

    @staticmethod
    def _text_from(path, stdout):
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
        # Older/newer Voxtype builds may report the result in JSON even when
        # the file was removed by a failed transcription.  Accept that as a
        # compatibility fallback, but never treat arbitrary stdout as text.
        try:
            payload = json.loads(stdout or "")
        except (TypeError, ValueError):
            return ""
        return str(payload.get("text", "")).strip() if isinstance(payload, dict) else ""

    def stop(self, timeout=120):
        with self.lock:
            if not self.active:
                return ""
            path = self.path
            try:
                result = self._run(["record", "stop", "--wait", "--json",
                                    "--timeout", str(int(timeout)), "--wait-file", str(path)], timeout + 5,
                                    allowed=(0, 3))
            except VoxtypeError:
                # A failed stop must not leave a future Peek session attached
                # to a stale transcript path or be mistaken for an active mic.
                self.active = False
                if path:
                    path.unlink(missing_ok=True)
                self.path = None
                raise
            try:
                return self._text_from(path, result.stdout)
            finally:
                self.active = False
                path.unlink(missing_ok=True)
                self.path = None

    def cancel(self):
        with self.lock:
            path = self.path
            if self.active:
                try:
                    self._run(["record", "cancel"], 10)
                except VoxtypeError:
                    # The daemon may already have completed/cancelled the
                    # request.  Cleanup is still safer than retrying a stale
                    # recording on the next toggle.
                    pass
            self.active = False
            if path:
                path.unlink(missing_ok=True)
            self.path = None
