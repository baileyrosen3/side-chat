<div align="center">
  <h1>Side Chat</h1>
  <p><strong>A native, screen-edge AI workspace for Omarchy.</strong></p>
  <p>Keep your coding-agent sessions close, continue them in a terminal, and optionally give them a local voice and a visible desktop companion.</p>
  <p><a href="#install">Install</a> · <a href="#keybindings">Keybindings</a> · <a href="#update">Update</a> · <a href="#privacy-and-safety">Privacy</a></p>
</div>

![Side Chat open at the left edge of an Omarchy desktop](preview.png)

Side Chat turns the agent you already use—**OMP, Pi, Codex, or Claude**—into a compact edge drawer that feels like part of Omarchy. Conversations persist, native tools and approvals stay intact, and one click hands the exact session to your terminal.

Add **Peek**, the optional Jarvis-style companion, for local speech recognition, spoken replies, fast desktop commands, and visible computer control. The microphone is off until you turn it on.

<details>
<summary><strong>See history, settings, permissions, and Peek</strong></summary>

### Find any conversation

![Searchable conversation history](screenshots/history.png)

### Configure the workspace, agent, and model

<p align="center">
  <img src="screenshots/preferences.png" alt="Side Chat preferences" width="48%">
  <img src="screenshots/permissions.png" alt="Per-conversation Codex permission modes" width="48%">
</p>

### Let Peek stay nearby

<p align="center">
  <img src="screenshots/peek.png" alt="Peek companion at the screen edge" width="43%">
  <img src="screenshots/peek-controls.png" alt="Peek voice and action controls" width="49%">
</p>

All screenshots use fixture content. No microphone, provider session, or private desktop content was captured.

</details>

## Your agent, without another terminal in the way

Move to the lower-left edge of either display and Side Chat peels into view. Leave it and the preview disappears; click or type and it stays open. Replies keep running when the panel closes, short conversations stay compact, and long ones scroll naturally.

This is not a second AI account or a web wrapper. Side Chat uses your installed CLI, its authentication, its provider, and its native conversation format. Start in the drawer, continue the same session in a full terminal, then return without losing the thread.

## What it does

### Native agent sessions

- Runs persistent **OMP, Pi, Codex, and Claude** sessions with streaming replies, native tool activity, questions, and approvals.
- Hands the exact session to Omarchy's configured terminal and syncs it back when you exit.
- Supports edit-and-retry branching without undoing changes already made to your files.
- Keeps model, reasoning, working-folder, Bash-approval, and permission choices with each conversation.
- Provides text adapters for OpenCode, Gemini, Copilot, Crush, and Grok when a native protocol is not available.

### A compact Omarchy interface

- Follows the live Omarchy theme, active-window border, scale, and multi-monitor layout.
- Includes searchable history, drafts, rename, delete, Markdown export, file drop, and clipboard image paste.
- Renders selectable Markdown and fenced code with dedicated copy actions.
- Opens from the screen edge or IPC, with no replacement bar widget and no overwritten keybindings.

### Peek: local voice and visible control

- Uses local Parakeet speech recognition and Pocket TTS by default; optional Kokoro and legacy ASR are available.
- Offers wake phrase, hands-free follow-ups, barge-in, mute, stop, and device selection.
- Handles common volume, brightness, media, app, workspace, timer, and web commands locally.
- Can operate accessible desktop controls or an isolated Chromium session while showing action state, verification, and a stop control.
- Stores opt-in memories, routines, watches, and tracked config restore points in local SQLite.

## Supported agents

| Agent | Session integration | Images | Per-chat permissions | Peek |
| --- | --- | --- | --- | --- |
| OMP | Native RPC | Yes | Default, Ask, Allow writes, YOLO | Yes |
| Pi | Native RPC | Yes | Default, Ask before tools | Yes |
| Codex | Native app server | Yes | Default, Read-only, Workspace, Auto review, Full access | Yes |
| Claude | Native stream JSON | Yes | Default plus Claude permission modes | Yes |
| OpenCode | Text adapter | Yes | Chat only, Auto approve | Chat only |
| Gemini, Copilot, Crush, Grok | Text adapters | Text attachments | CLI-managed | Chat only |

The selected CLI and model determine provider costs and model capabilities. Side Chat does not create another provider account.

## Install

### Requirements

- Omarchy with the **Quickshell plugin system (Quattro)** in a Hyprland session
- Linux x86_64 for Peek's currently pinned binaries
- One installed and authenticated agent CLI
- Internet access during setup; Peek's models and CPU runtime require several gigabytes

Older Waybar-based Omarchy releases are not supported.

### 1. Install chat

Run this in your normal desktop terminal:

```bash
omarchy pkg add python git
omarchy plugin add "https://github.com/baileyrosen3/side-chat"
```

If Omarchy asks whether to enable the plugin immediately, choose **No** until setup finishes. Then run:

```bash
cd ~/.config/omarchy/plugins/blr.side-chat
python3 setup.py
omarchy plugin enable blr.side-chat
omarchy-shell blr.side-chat open
```

Run setup without `sudo`; Omarchy will request privileges for system packages when needed. Setup installs the chat dependencies and checks the selected default agent. If no agent is configured, choose one through **Setup → Default Agent** or, for example:

```bash
omarchy default agent codex
```

Complete that CLI's provider sign-in in its terminal, then verify the install with `python3 setup.py --check`.

### 2. Add Peek voice and computer control (optional)

With Peek powered off and no reply running:

```bash
cd ~/.config/omarchy/plugins/blr.side-chat
python3 setup.py --with-peek
python3 setup.py --check --with-peek
```

This installs the CPU speech runtime, verified local models, audio tools, accessible-app support, and isolated-browser tooling. Existing compatible Voxtype files are reused. Setup does not turn on the microphone.

Native mouse and keyboard control, physical takeover detection, and the emergency **Ctrl+Alt+Esc** shortcut require the explicit desktop-input option:

```bash
python3 setup.py --with-peek --with-desktop-input
```

This installs named udev/module configuration and grants your active seat access to input and virtual-input devices. It does not run the agent as root or add your user to the `input` group. Log out and back in if the final device check asks you to.

Optional engines include `python3 setup.py --with-kokoro` and `python3 setup.py --with-legacy-asr`; both imply Peek setup.

## Keybindings

Side Chat never edits `~/.config/hypr/bindings.lua`. These are the maintainer's exact Jarvis/Peek bindings: physical numpad **0** opens or closes Peek, and numpad **decimal** toggles its microphone, with Num Lock either on or off.

```lua
-- Peek / Jarvis: bare numpad shortcuts, with Num Lock on or off.
o.bind("KP_0", "Toggle Peek", "omarchy-shell blr.side-chat peek")
o.bind("KP_Insert", "Toggle Peek", "omarchy-shell blr.side-chat peek")
o.bind("KP_Decimal", "Toggle Peek microphone", "omarchy-shell blr.side-chat peekToggleMicrophone")
o.bind("KP_Delete", "Toggle Peek microphone", "omarchy-shell blr.side-chat peekToggleMicrophone")
```

`KP_0` and `KP_Insert` are the same physical key in the two Num Lock states; so are `KP_Decimal` and `KP_Delete`. To bind the chat drawer instead, map any unused key to `omarchy-shell blr.side-chat toggle`.

After editing bindings:

```bash
hyprctl reload
hyprctl configerrors
```

The second command should report no errors.

## Use

Move the pointer into the bottom 160 scaled pixels of the left screen edge. Click or type to pin the panel open; use Escape, Close, or click outside to dismiss it.

| Shortcut | Action |
| --- | --- |
| Enter | Send |
| Shift+Enter | New line |
| Ctrl+N | New conversation |
| Ctrl+H | History |
| Ctrl+Shift+V | Paste a clipboard image |
| Ctrl+Shift+C | Copy the last message |
| Escape | Dismiss the panel |

Useful IPC commands:

| Command | Result |
| --- | --- |
| `omarchy-shell blr.side-chat toggle` | Open or close chat |
| `omarchy-shell blr.side-chat open` | Open chat |
| `omarchy-shell blr.side-chat newChat` | Start a conversation |
| `omarchy-shell blr.side-chat peek` | Open or close Peek |
| `omarchy-shell blr.side-chat peekToggleMicrophone` | Toggle Peek's microphone |
| `omarchy-shell blr.side-chat companionControls` | Open Peek controls |
| `omarchy-shell blr.side-chat status \| jq` | Show live plugin status |

`openOnScreen DP-1` and `peekOnScreen DP-3` target a specific monitor. `peekSettings` opens advanced voice and control settings. Selecting a microphone does not enable listening.

## Permissions and terminal handoff

Click the shield above the composer or enter `/permissions` to choose access for the current conversation. Side Chat restarts the idle native session with that policy; it never rewrites the CLI's global configuration. Full-access modes can execute commands and change files, so review the selected mode before sending a task.

For Claude and Codex, **Always allow Bash** approves future Bash requests only in the current conversation. File edits, MCP approvals, managed network requests, and agent questions remain separate. Pi's **Ask before tools** is an approval extension, not a sandbox.

Click **Terminal** after the first prompt to continue that exact native session in Omarchy's terminal. An exclusive lock prevents the panel and terminal from writing simultaneously. Exit the agent in the terminal to return ownership to Side Chat.

## Update

Finish the active reply and power Peek off, then run:

```bash
omarchy plugin update blr.side-chat --yes
cd ~/.config/omarchy/plugins/blr.side-chat
python3 setup.py
omarchy restart shell
omarchy-shell blr.side-chat open
```

If you installed Peek, use `python3 setup.py --with-peek` instead and include any optional engine or desktop-input flags you use.

`omarchy plugin update` updates the Git checkout, but it does not rerun dependency setup. A hot plugin rescan can also leave older nested QML types cached inside the long-running shell. **`omarchy restart shell` is therefore the reliable step that loads the new UI.** The final command opens it again.

`--yes` skips Omarchy's trusted-plugin review prompt. Without it, Omarchy prints the incoming Git diff and asks for confirmation. **That diff is terminal output, not a file or an error.**

Verify the installed commit, manifest, and running UI:

```bash
git -C ~/.config/omarchy/plugins/blr.side-chat log -1 --oneline
jq -r .version ~/.config/omarchy/plugins/blr.side-chat/manifest.json
omarchy-shell blr.side-chat status | jq -r '.uiVersion, .uiSource'
```

The manifest and `uiVersion` should match, and `uiSource` should point inside `~/.config/omarchy/plugins/blr.side-chat`.

## Privacy and safety

- Chat history and preferences stay in `~/.local/state/omarchy/side-chat/chats.sqlite3`; attachments are snapshotted beside it. The state directory is private (`0700`).
- Credentials remain with the selected CLI. Prompts and attachments go to that CLI's configured provider under its terms.
- Speech recognition and synthesis run locally after setup. There is no cloud speech service, raw microphone recordings are not saved, and the microphone is off by default.
- Screen context is off or on-request according to your setting. There is no background screenshot recording or clipboard history.
- Desktop input access is optional. Peek pauses automation when it detects physical takeover and exposes Stop; **Ctrl+Alt+Esc** is the emergency stop when native input support is installed.
- Memories, routines, watches, action history, and tracked config restore points are local. Normal agent edits and arbitrary desktop actions are not automatically undoable.

Set `SIDE_CHAT_STATE` for an isolated state directory or `SIDE_CHAT_DATA` for the speech runtime and models. Deleting a conversation currently leaves attachment snapshots and native session files on disk.

## Troubleshooting

<details>
<summary><strong>The update completed, but I still see the old UI</strong></summary>

Run the three verification commands in [Update](#update), then `omarchy restart shell` and reopen Side Chat. If the plugin directory has no `.git`, back it up, remove the older copy install, and reinstall with `omarchy plugin add`.

</details>

<details>
<summary><strong>The updater filled my terminal with a Git diff</strong></summary>

That is Omarchy's review screen. Confirm it at the prompt, or rerun `omarchy plugin update blr.side-chat --yes` for this trusted plugin.

</details>

<details>
<summary><strong>An agent, microphone, model, or control dependency is unavailable</strong></summary>

Run `python3 setup.py --check` with the same Peek, engine, and desktop-input flags you installed. Checks do not download models, start the microphone, or send an agent request. Agent authentication must be completed in that CLI's terminal. Audio devices remain managed by PipeWire/Omarchy. Browser mode can work without native desktop-input access.

</details>

<details>
<summary><strong>Setup or a model download was interrupted</strong></summary>

Rerun setup with the same flags. Completed, verified downloads and existing compatible models are reused.

</details>

## Disable or remove

```bash
omarchy plugin disable blr.side-chat
omarchy plugin enable blr.side-chat
omarchy plugin remove blr.side-chat
```

Removal deletes the Git checkout but keeps chat history, attachments, speech models, and the local runtime for a future reinstall. Remove `~/.local/state/omarchy/side-chat` and `~/.local/share/side-chat` manually only if you also want to erase that data; shared Voxtype and Hugging Face caches may belong to other applications.

If you installed Side Chat's desktop-input rules and want to remove them:

```bash
sudo rm /etc/udev/rules.d/70-side-chat-input.rules /etc/modules-load.d/side-chat-input.conf
sudo udevadm control --reload-rules
```

Reboot to clear existing device access. Shared Arch packages are intentionally left installed.

## Development

```bash
python3 -B -m unittest discover -s tests -v
bun tests/test_pi_permissions.ts
python3 setup.py --check
git diff --check
```

Visual fixture preview:

```bash
ln -s /usr/share/omarchy/shell/Commons Commons
quickshell --no-duplicate -p DesignPreview.qml
```

The preview uses synthetic messages and does not connect an agent or microphone. `Commons` is a development-only import link and must not be committed.

Qt rendering checks require a graphical session:

```bash
QT_QPA_PLATFORMTHEME=generic QT_QUICK_CONTROLS_STYLE=Basic QT_QUICK_BACKEND=rhi QSG_RHI_BACKEND=opengl /usr/lib/qt6/bin/qmltestrunner -input tests/qml -import tests/qml/imports -v1
```

Before publishing, validate a clean clone with `omarchy plugin validate .` and complete [TEST_PLAN.md](TEST_PLAN.md). See [implementation notes](docs/implementation.md), the [speech audit](docs/speech-audit.md), and the [publishing checklist](docs/publishing.md) for the deeper protocol, safety, and release details.

## License and attribution

The original Side Chat source remains under the [MIT license](LICENSE). Peek's interface, integration, and original procedural 3D companion are under [GPL-3.0-or-later](COPYING.JARVIS); distribute the combined plugin under GPL-3.0-or-later while preserving the MIT notices.

Runtime dependencies, model licenses, voice attribution, and pinned revisions are documented in [THIRD_PARTY.md](THIRD_PARTY.md). The companion uses original procedural geometry and shaders—there are no purchased or downloaded character assets.
