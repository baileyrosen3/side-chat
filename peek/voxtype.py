# SPDX-License-Identifier: GPL-3.0-or-later
"""Small file-backed bridge to the user's Voxtype daemon.

Voxtype owns microphone capture and ASR in this mode.  Peek asks the daemon to
write one transcript to a private file, then reads that file after recording
finishes. Recording control and transcripts use the CLI/file contract. Optional
level telemetry reads the daemon's audio socket without capturing audio or
loading another model; losing telemetry never prevents transcription.
"""
import json
import math
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import threading
import time


class VoxtypeError(RuntimeError):
    """A user-actionable Voxtype integration failure."""


def compatibility_problem():
    # Check the running daemon, not the CLI on PATH: signal-only clients can
    # control a newer daemon installed through a systemd user override.
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'voxtype'
    try:
        version = (runtime / 'version').read_text().strip()
    except OSError:
        return None  # Older daemons may not publish a version; not a capability probe.
    if version == '1.0.1':
        return ('Peek requires a fixed Voxtype daemon: unpatched 1.0.1 can type streaming recordings '
                'into the focused app instead of the private transcript. See docs/voxtype.md '
                'for the pinned build, or select a downloaded local recognizer.')
    return None


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
        self.runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'voxtype'
        self.meter = None
        self.meter_pending = b''
        self.meter_retry = 0

    def status(self):
        result = self._run(['status', '--format', 'json'], 3)
        try:
            return json.loads(result.stdout)['alt']
        except (ValueError, KeyError, TypeError) as exc:
            raise VoxtypeError('Could not read Voxtype status. Check that its daemon is running.') from exc

    def level(self):
        """Read optional level metadata, never open another microphone stream.

        Voxtype broadcasts native-endian (sequence, min, max, dBFS) frames.
        Missing telemetry must not prevent transcription on older daemons.
        Drain at 10 Hz; a slow consumer otherwise gets disconnected upstream.
        """
        if not self.active:
            return 0.0
        try:
            if self.meter is None:
                if time.monotonic() < self.meter_retry:
                    return 0.0
                self.meter_retry = time.monotonic() + 1
                self.meter = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.meter.settimeout(.05)
                self.meter.connect(str(self.runtime / 'audio.sock'))
                self.meter.setblocking(False)
            peak = 0.0
            for _ in range(16):
                try:
                    data = self.meter.recv(4096)
                except BlockingIOError:
                    break
                if not data:
                    self.close_meter()
                    break
                self.meter_pending += data
                size = len(self.meter_pending) // 16 * 16
                for _, low, high, _ in struct.iter_unpack('=Ifff', self.meter_pending[:size]):
                    if math.isfinite(low) and math.isfinite(high):
                        peak = max(peak, abs(low), abs(high))
                self.meter_pending = self.meter_pending[size:]
            return min(1.0, peak * 3)
        except OSError:
            self.close_meter()
            return 0.0

    def close_meter(self):
        if self.meter is not None:
            self.meter.close()
        self.meter = None
        self.meter_pending = b''

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
            if problem := compatibility_problem():
                raise VoxtypeError(problem)
            if self.status() != 'idle':
                raise VoxtypeError('Voxtype is busy. Finish regular dictation before starting the Peek microphone.')
            self.sequence += 1
            self.path = self.directory / f"transcript-{os.getpid()}-{self.sequence}.txt"
            self.path.unlink(missing_ok=True)
            # File mode is explicit so Peek never types into whichever app is
            # currently focused.  Peek owns the submit step after reading it.
            self._run(["record", "start", f"--file={self.path}", "--no-osd", "--no-auto-submit"], 10)
            self.active = True
            # Sending a signal is not confirmation that capture has started.
            deadline = time.monotonic() + 3
            try:
                while self.status() not in ('recording', 'streaming'):
                    if time.monotonic() >= deadline:
                        raise VoxtypeError('Voxtype did not start recording. Check its microphone and daemon log.')
                    time.sleep(.05)
            except Exception:
                self.cancel()
                raise

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
            self.close_meter()
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
            self.close_meter()
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
