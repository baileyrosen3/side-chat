"""Cursor IPC regressions use a fake compositor, never stall the real desktop."""
import json
import os
from pathlib import Path
import select
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest

from companion_cursor import cursor_position

ROOT = Path(__file__).resolve().parents[1]


class FakeCompositor:
    def __init__(self, path):
        self.path = str(path)
        self.payload = b'{"x":-1400,"y":2100}'
        self.delay = .001
        self.stall = False
        self.requests = []
        self.closed = []
        self.stop = threading.Event()
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(self.path)
        self.socket.listen()
        self.socket.settimeout(.05)
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        while not self.stop.is_set():
            try:
                peer, _ = self.socket.accept()
            except TimeoutError:
                continue
            with peer:
                peer.settimeout(1)
                accepted = time.monotonic()
                try:
                    request = peer.recv(128)
                    self.requests.append((time.monotonic(), time.monotonic() - accepted, request))
                    if not self.stall:
                        payload = self.payload
                        for byte in payload:
                            peer.sendall(bytes([byte]))
                            time.sleep(self.delay)
                    peer.recv(16)
                except (OSError, TimeoutError):
                    pass
                self.closed.append(time.monotonic() - accepted)

    def close(self):
        self.stop.set()
        self.thread.join(timeout=2)
        self.socket.close()


class CursorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="peek-test-")
        self.addCleanup(self.temp.cleanup)
        self.server = FakeCompositor(Path(self.temp.name) / "cursor.sock")
        self.addCleanup(self.server.close)

    def worker(self, stdout=subprocess.PIPE):
        process = subprocess.Popen(["python3", "-B", "-u", str(ROOT / "companion_cursor.py"), self.server.path],
                                   stdin=subprocess.PIPE, stdout=stdout, stderr=subprocess.PIPE)
        def cleanup():
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=2)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream:
                    stream.close()
        self.addCleanup(cleanup)
        return process

    def sample(self, process, timeout=3):
        self.assertTrue(select.select([process.stdout], [], [], timeout)[0], "No worker update")
        return json.loads(process.stdout.readline())

    def test_fragmented_coordinates_and_invalid_replies(self):
        self.assertEqual(cursor_position(self.server.path), {"valid": True, "x": -1400, "y": 2100})
        for payload in (b'{"x":true,"y":0}', b'{"x":NaN,"y":0}', b'[]', b'{"x":1}', b'x' * 257):
            with self.subTest(payload=payload[:40]):
                self.server.payload = payload
                self.server.delay = 0
                with self.assertRaises((ValueError, TimeoutError)):
                    cursor_position(self.server.path)

    def test_total_deadline_covers_trickled_response(self):
        self.server.delay = .04
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            cursor_position(self.server.path, timeout=.12)
        self.assertLess(time.monotonic() - started, .3)

    def test_unchanged_samples_rate_limit_and_owner_exit(self):
        process = self.worker()
        self.assertTrue(self.sample(process)["valid"])
        time.sleep(.65)
        self.assertFalse(select.select([process.stdout], [], [], 0)[0], "Unchanged position emitted again")
        times = [request[0] for request in self.server.requests]
        self.assertGreater(len(times), 2)
        self.assertTrue(all(b - a >= .12 for a, b in zip(times, times[1:])))
        self.assertTrue(all(request[2] == b'j/cursorpos' for request in self.server.requests))
        process.stdin.close()
        self.assertEqual(process.wait(timeout=.5), 0)

    def test_stalled_peer_closes_then_backs_off_and_recovers(self):
        self.server.stall = True
        process = self.worker()
        self.assertEqual(self.sample(process), {"valid": False})
        time.sleep(.1)
        self.assertLess(self.server.closed[0], .35)
        count = len(self.server.requests)
        self.server.stall = False
        time.sleep(.4)
        self.assertEqual(len(self.server.requests), count)
        self.assertTrue(self.sample(process)["valid"])

    def test_full_output_pipe_does_not_hold_compositor_socket(self):
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        self.addCleanup(os.close, write_fd)
        os.set_blocking(write_fd, False)
        try:
            while True:
                os.write(write_fd, b'x' * 4096)
        except BlockingIOError:
            pass
        self.worker(stdout=write_fd)
        time.sleep(.35)
        self.assertEqual(self.server.requests, [], "Do not query while the UI pipe is full")
        os.set_blocking(read_fd, False)
        while True:
            try:
                os.read(read_fd, 65536)
            except BlockingIOError:
                break
        self.assertTrue(select.select([read_fd], [], [], 1)[0])
        self.assertTrue(json.loads(os.read(read_fd, 4096))["valid"])
        time.sleep(.1)
        self.assertLess(self.server.closed[0], .15)

    @unittest.skipUnless(shutil.which("quickshell"), "Quickshell is not installed")
    def test_qml_busy_gui_does_not_delay_compositor_request(self):
        # Enable the reader, then deliberately occupy ONLY this windowless test
        # shell's GUI. The former QML Socket left the server waiting for this.
        directory = Path(os.environ.get("PEEK_CURSOR_QML_DIR", ROOT))
        config = Path(self.temp.name) / "shell.qml"
        config.write_text('''import QtQuick
import Quickshell
import Quickshell.Io
import "file:''' + str(directory) + '''"
ShellRoot {
    property int changes: 0
    CompanionCursor {
        id: cursor
        socketPath: Quickshell.env("PEEK_CURSOR_TEST_SOCKET")
        onPositionChanged: changes++
    }
    IpcHandler {
        target: "peek-test"
        function startBusy(): void {
            cursor.enabled = true;
            var end = Date.now() + 500;
            while (Date.now() < end) {}
        }
        function disable(): void { cursor.enabled = false }
        function status(): string { return JSON.stringify({valid:cursor.valid,x:cursor.position.x,changes:changes}) }
        function finish(): void { Qt.quit() }
    }
    Timer { interval: 10000; running: true; onTriggered: Qt.quit() }
}
''')
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="generic",
                   PEEK_CURSOR_TEST_SOCKET=self.server.path, QS_DISABLE_FILE_WATCHER="1")
        log = open(Path(self.temp.name) / "shell.log", "w+")
        self.addCleanup(log.close)
        process = subprocess.Popen(["quickshell", "-p", str(config)], env=env, stdout=log, stderr=log)
        def ipc(method):
            return subprocess.check_output(["quickshell", "-p", str(config), "ipc", "call", "peek-test", method],
                                           text=True, stderr=subprocess.DEVNULL, timeout=3).strip()
        try:
            for _ in range(30):
                try:
                    state = json.loads(ipc("status"))
                    break
                except subprocess.CalledProcessError:
                    time.sleep(.05)
            else:
                log.seek(0)
                self.fail(log.read())
            self.assertFalse(state["valid"])
            self.assertEqual(self.server.requests, [])
            ipc("startBusy")
            time.sleep(.15)
            self.assertTrue(self.server.requests)
            delay = self.server.requests[0][1]
            self.assertLess(delay, .15, f"Compositor waited {delay:.3f}s for busy GUI")
            state = json.loads(ipc("status"))
            self.assertTrue(state["valid"])
            self.assertEqual(state["x"], -1400)
            time.sleep(.3)
            self.assertEqual(json.loads(ipc("status"))["changes"], state["changes"])
            ipc("disable")
            time.sleep(.15)
            count = len(self.server.requests)
            time.sleep(.3)
            self.assertEqual(len(self.server.requests), count)
            self.assertFalse(json.loads(ipc("status"))["valid"])
            print(f"\nBusy GUI regression: compositor request arrived in {delay * 1000:.2f} ms", flush=True)
        finally:
            if process.poll() is None:
                try:
                    ipc("finish")
                    process.wait(timeout=2)
                except (subprocess.SubprocessError, OSError):
                    process.terminate()
                    process.wait(timeout=2)


if __name__ == "__main__":
    unittest.main()
