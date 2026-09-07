#!/usr/bin/env python3
"""Own the native session while its real CLI runs in the user's terminal."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from agent_session import SessionLease


def main():
    folder = Path(sys.argv[1])
    marker = folder / "terminal.json"
    record = json.loads(marker.read_text())
    lease = SessionLease(folder)
    record.update(status="running", pid=os.getpid(), time=time.time())
    marker.write_text(json.dumps(record))
    try:
        return subprocess.call(record["argv"], cwd=record["cwd"])
    finally:
        record.update(status="closed", time=time.time())
        marker.write_text(json.dumps(record))
        lease.close()


if __name__ == "__main__":
    raise SystemExit(main())
