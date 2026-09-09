#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Isolate Hyprland cursor requests from Quickshell's GUI/render thread.

Hyprland's control callback polls an accepted socket for up to five seconds.
A Qt socket whose write waits for the GUI loop can stall the compositor there.
This single worker sends immediately after connecting and closes the socket
before publishing to QML. Neither rendering nor a full stdout pipe can hold an
open compositor transaction. It exits when its owner's stdin closes.
"""
import json
import math
import os
import select
import socket
import sys
import time

ACTIVE_INTERVAL = 0.125
IDLE_INTERVAL = 0.250
RETRY_INTERVAL = 2.0
REQUEST_TIMEOUT = 0.200
MAX_REPLY = 256


def cursor_position(path, timeout=REQUEST_TIMEOUT):
    deadline = time.monotonic() + timeout
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        def remaining():
            seconds = deadline - time.monotonic()
            if seconds <= 0:
                raise TimeoutError("Cursor request timed out")
            connection.settimeout(seconds)

        remaining()
        connection.connect(path)
        # No event loop, stdout write, or parent interaction between these.
        remaining()
        connection.sendall(b"j/cursorpos")
        response = bytearray()
        while len(response) <= MAX_REPLY:
            remaining()
            data = connection.recv(MAX_REPLY + 1 - len(response))
            if not data:
                raise ValueError("Incomplete cursor reply")
            response.extend(data)
            if len(response) > MAX_REPLY:
                break
            try:
                point = json.loads(response)
            except (ValueError, UnicodeError):
                continue
            if not isinstance(point, dict) or any(
                type(point.get(axis)) not in (int, float) or not math.isfinite(point[axis])
                for axis in ("x", "y")
            ):
                raise ValueError("Invalid cursor coordinates")
            return {"valid": True, "x": point["x"], "y": point["y"]}
        raise ValueError("Oversized cursor reply")


def publish(output_fd, sample):
    # Small writes to a nonblocking pipe are atomic. Drop a sample if QML is
    # busy; retry the newest position on the next tick without building a queue.
    try:
        os.write(output_fd, (json.dumps(sample, separators=(",", ":")) + "\n").encode())
        return True
    except BlockingIOError:
        return False


def run(path, input_fd=0, output_fd=1):
    os.set_blocking(output_fd, False)
    previous = None
    sent = None
    moved_at = time.monotonic()
    interval = 0.0
    while True:
        if select.select([input_fd], [], [], interval)[0]:
            if not os.read(input_fd, 4096):
                return
        # Stop polling while the UI isn't consuming updates. No socket is open.
        if not select.select([], [output_fd], [], 0)[1]:
            interval = IDLE_INTERVAL
            continue
        started = time.monotonic()
        try:
            sample = cursor_position(path)
            now = time.monotonic()
            if sample != previous:
                moved_at = now
            previous = sample
            interval = IDLE_INTERVAL if now - started > .032 or now - moved_at > 1.5 else ACTIVE_INTERVAL
        except (OSError, ValueError, OverflowError):
            sample = {"valid": False}
            previous = None
            interval = RETRY_INTERVAL
        # cursor_position has already closed the compositor socket here.
        if sample != sent and publish(output_fd, sample):
            sent = sample


if __name__ == "__main__":
    try:
        run(sys.argv[1])
    except (BrokenPipeError, ConnectionResetError):
        pass
