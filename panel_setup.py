#!/usr/bin/env python3
"""Move Side Chat's old service entry onto the Omarchy bar, preserving settings."""
import argparse
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile

PLUGIN = "blr.side-chat"


def entry_id(entry):
    return entry.get("id") if isinstance(entry, dict) else entry


def panel_config(config):
    result = copy.deepcopy(config)
    layout = result.setdefault("bar", {}).setdefault("layout", {})
    for section in ("left", "center", "right"):
        layout.setdefault(section, [])
    plugins = result.get("plugins", [])
    old = next((p for p in plugins if entry_id(p) == PLUGIN), {"id": PLUGIN})
    if not any(entry_id(p) == PLUGIN for rows in layout.values() for p in rows):
        layout["left"].append(old)
    result["plugins"] = [p for p in plugins if entry_id(p) != PLUGIN]
    if "disabledPlugins" in result:
        result["disabledPlugins"] = [p for p in result["disabledPlugins"] if p != PLUGIN]
    return result


def enable_panel(path, check=False):
    before = path.read_bytes() if path.exists() else b'{}'
    after = panel_config(json.loads(before))
    if after == json.loads(before):
        return None
    if check:
        return after
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name("shell.json.before-side-chat-panel-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        shutil.copy2(path, backup)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as staged:
        json.dump(after, staged, indent=2)
        staged.write("\n")
        staged.flush()
        os.fsync(staged.fileno())
    try:
        # Do not overwrite a bar edit made while preparing the migration.
        if (path.read_bytes() if path.exists() else b'{}') != before:
            raise RuntimeError("Shell settings changed; run the migration again.")
        if path.exists():
            shutil.copymode(path, staged.name)
        os.replace(staged.name, path)
    finally:
        Path(staged.name).unlink(missing_ok=True)
    return after


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Preview without changing shell.json")
    args = parser.parse_args()
    path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "omarchy/shell.json"
    changed = enable_panel(path, args.check)
    print("Side Chat is already on the bar." if changed is None else
          "Side Chat will move to the left bar; other settings are preserved." if args.check else
          "Side Chat is on the bar. Previous shell.json saved beside the current file.")
