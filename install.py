#!/usr/bin/env python3
"""Copy a development build into Omarchy. For Git installs use setup.py instead."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

FILES = ["manifest.json", "Main.qml", "ChatWindow.qml", "MessageCard.qml", "ActionButton.qml",
         "Icon.qml", "Theme.js", "Markdown.js", "backend.py", "agent_session.py", "native_bridge.py",
         "terminal_session.py", "ToolActivity.qml", "AgentPrompt.qml", "JarvisView.qml", "JarvisBuddy.qml",
         "AgentPointer.qml", "JarvisSettings.qml", "CompanionSettings.qml", "CompanionWindow.qml", "CompanionSurface.qml", "RoundedGeometry.qml", "VoiceStatus.js", "COPYING.JARVIS", "THIRD_PARTY.md", "README.md", "LICENSE"]
FILES += ["RobotExpressions.js", "CompanionMotion.qml", "RobotAppearance.qml", "PeekModel.qml",
          "RobotFace.qml", "SculptGeometry.qml", "assets/companion/studio.hdr",
          "assets/companion/face.vert", "assets/companion/face.frag"]
FILES += ["docs/speech-audit.md", "docs/implementation.md", "docs/publishing.md", "setup.py",
          "deploy/70-side-chat-input.rules", "deploy/side-chat-input.conf"]
FILES += sorted(str(p.relative_to(Path(__file__).parent)) for p in (Path(__file__).parent / "jarvis").rglob("*")
                if p.is_file() and "__pycache__" not in p.parts and p.suffix in (".py", ".ts", ".txt", ".json", ".yaml", ".rs", ".toml", ".lock"))
FILES += sorted(str(p.relative_to(Path(__file__).parent)) for p in (Path(__file__).parent / "agents").glob("*.py"))
FILES += ["WindowBorder.js", "WindowBorder.qml", "DrawerSurface.qml", "LookSettings.qml", "BashApprovalSettings.qml"]
FILES += ["permission_modes.py", "PermissionSettings.qml", "agents/pi_permissions.ts"]
FILES += ["ChatStyle.qml", "ChatField.qml", "ChatComboBox.qml"]
FILES += ["CompanionCursor.qml", "CompanionGaze.js", "companion_cursor.py"]
FILES += ["ChatSection.qml", "ChatSwitch.qml", "ChatSpinBox.qml", "ChatScrollBar.qml"]
FILES += ["TaskDetails.qml", "CompanionTransition.qml"]
FILES += ["preview.png", "screenshots/history.png", "screenshots/preferences.png",
          "screenshots/permissions.png", "screenshots/peek.png", "screenshots/peek-controls.png"]
PLUGIN = "blr.side-chat"


def check_destination(destination):
    if destination.is_symlink() or (destination / ".git").exists():
        raise SystemExit("This destination is a linked or Git-managed plugin. Use "
                         "`omarchy plugin update blr.side-chat` and `python3 setup.py` "
                         "inside its checkout; the development installer must not replace it.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Show and validate the install without changing desktop config")
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "omarchy"
    destination = config / "plugins" / PLUGIN
    check_destination(destination)
    for name in FILES:
        if not (source / name).is_file():
            raise SystemExit(f"Missing source file: {name}")
    for binary in ("python3", "omarchy", "omarchy-shell", "quickshell"):
        if not shutil.which(binary):
            raise SystemExit(f"Install requires {binary} on PATH.")
    if json.loads((source / "manifest.json").read_text())["id"] != PLUGIN:
        raise SystemExit("Unexpected plugin manifest.")
    for script in ("backend.py", "companion_cursor.py"):
        compile((source / script).read_text(), script, "exec")
    print(f"Install {len(FILES)} files to {destination}", flush=True)
    if args.check:
        return
    # Do not interrupt an active conversation during an update.
    for command in (["omarchy-shell", PLUGIN, "status"],
                    ["quickshell", "-p", str(source / "shell.qml"), "ipc", "call", PLUGIN, "status"]):
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            try:
                if json.loads(result.stdout).get("busy"):
                    raise SystemExit("A reply is still running. Finish or stop it, then run the installer again.")
            except json.JSONDecodeError:
                pass
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = config / "plugin-backups" / (PLUGIN + "." + stamp)
    backup.mkdir(parents=True)
    if (config / "shell.json").exists():
        shutil.copy2(config / "shell.json", backup / "shell.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="side-chat-stage-", dir=backup) as staging:
        staged = Path(staging) / PLUGIN
        staged.mkdir()
        # Fresh component URLs bypass Qt's cached nested QML without restarting
        # the shared shell (which also owns the user's lock screen).
        release_name='runtime-'+stamp
        release=staged/release_name
        release.mkdir()
        for name in FILES:
            (release / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, release / name)
        manifest=json.loads((source/'manifest.json').read_text())
        manifest['entryPoints']['service']=release_name+'/Main.qml'
        (staged/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        for name in ('README.md','LICENSE','COPYING.JARVIS','THIRD_PARTY.md','preview.png',
                     'screenshots/history.png','screenshots/preferences.png','screenshots/permissions.png',
                     'screenshots/peek.png','screenshots/peek-controls.png','docs/speech-audit.md',
                     'docs/implementation.md','docs/publishing.md'):
            (staged/name).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source/name,staged/name)
        if destination.exists():
            destination.rename(backup / "plugin")
        staged.rename(destination)
    # End the standalone preview before the shell starts the production bridge.
    for preview in ("shell.qml", "DesignPreview.qml"):
        subprocess.run(["quickshell", "-p", str(source / preview), "kill"], capture_output=True, timeout=5)
    subprocess.run(["omarchy-shell", "shell", "rescanPlugins"], check=True)
    # Plugin discovery runs asynchronously inside the shell.
    for _ in range(30):
        result = subprocess.run(["omarchy", "plugin", "enable", PLUGIN], capture_output=True, text=True)
        if result.returncode == 0:
            break
        time.sleep(0.2)
    else:
        raise SystemExit(result.stderr or result.stdout or "Could not enable the plugin.")
    for _ in range(30):
        result = subprocess.run(["omarchy-shell", PLUGIN, "status"], capture_output=True, text=True)
        try:
            status = json.loads(result.stdout)
            if (status.get("connected") and status.get('uiVersion')==manifest['version']
                    and '/'+release_name+'/' in status.get('uiSource','')):
                print(f"Installed and connected. Agent: {status.get('agent') or 'choose an Omarchy default agent'}. Backup: {backup}")
                return
        except (json.JSONDecodeError, TypeError):
            pass
        time.sleep(0.2)
    raise SystemExit("Plugin copied and enabled, but not ready. Inspect omarchy-shell logs.")


if __name__ == "__main__":
    main()
