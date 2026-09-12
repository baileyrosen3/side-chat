<div align="center">
  <h1>Side Chat</h1>
  <p><strong>One native workspace for Chat, Notes, To-dos, and Peek on Omarchy.</strong></p>
  <p>Keep your agent sessions close, talk to Peek, and jot down notes and to-dos without breaking your flow.</p>
  <p><a href="#meet-peek">Peek</a> · <a href="#thoughts-quick-notes-and-to-dos">Thoughts</a> · <a href="#install">Install</a> · <a href="#keybindings">Keybindings</a> · <a href="#update">Update</a> · <a href="#privacy-and-safety">Privacy</a></p>
</div>

<p align="center">
  <img src="screenshots/workspace-chat.png" alt="Side Chat with shared Chat, Notes, and To-dos tabs and Peek in the app header" width="400">
</p>

**Chat** turns the agent you already use—OMP, Pi, Codex, or Claude—into a compact edge drawer with persistent sessions, native tools, approvals, and terminal handoff. **Peek** adds hands-free local voice, durable memory, fast desktop commands, and visible computer control. **Notes and To-dos** share the same drawer, header, navigation, and Peek controls. The numpad groups web apps, workspace tabs, and tap-to-toggle listening into three rows. The workspace includes task reminders, selected-text capture, shared search, source links, and recovery while keeping the same three tabs.

Version **1.16.1** adds clearer controls, adaptive Notes, separate Stop and Redirect actions, safer draft recovery, and faster conversation rendering and search. It also fixes a startup lock conflict between reminder checks and saved drafts. See the [UI and interaction audit](docs/audit-fixes-2026-09-12.md) for the changes and validation.

## Meet Peek

**Peek is the voice and computer-control layer, with an animated robot body at the screen edge.** He listens only when enabled, speaks replies locally, and shows what the agent is doing while it works.

<p align="center">
  <img src="screenshots/peek.png" alt="Peek companion at the screen edge" width="42%">
  &nbsp;&nbsp;
  <img src="screenshots/peek-controls.png" alt="Peek voice controls and verified action summary" width="48%">
</p>

Peek can answer through the same native agent session as chat, but common desktop requests never need an LLM round trip. Volume, brightness, music, app launches, workspaces, timers, and explicit web URLs are handled locally. Larger tasks go to your selected agent with the active conversation, working folder, and permission mode preserved.

| Say something like… | What Peek does |
| --- | --- |
| “Set the volume to 30” | Runs a fast local command and checks the result |
| “Open my terminal” | Uses Omarchy's configured launcher |
| “Review this project and fix the tests” | Continues through your native coding-agent session |
| “Remember that I prefer compact windows” | Saves an explicit local memory you can inspect or delete |
| “Set a timer for twenty minutes” | Creates a persistent local watch and announces it when ready |

The companion surface keeps microphone, spoken-reply mute, Stop, conversation, Desktop/Browser, standby, and power controls within reach. Desktop actions can use accessible app controls, native input, or an isolated Chromium session. Peek shows recent action state and only says **Actions verified** when supported readback checks actually matched; otherwise it asks you to review the result.

Speech recognition and synthesis run locally after setup. Voxtype is the default recognition daemon; the microphone starts off, screen context follows your setting, and there is no background screenshot recording. The optional bundled wake model listens for **“Hey Jarvis”**; the assistant and on-screen character are named Peek. A different wake phrase requires a different detector model.

<details>
<summary><strong>See conversation history, settings, and permissions</strong></summary>

### Find any conversation

![Searchable conversation history](screenshots/history.png)

### Configure the workspace, agent, and model

<p align="center">
  <img src="screenshots/preferences.png" alt="Side Chat preferences" width="48%">
  <img src="screenshots/permissions.png" alt="Per-conversation Codex permission modes" width="48%">
</p>

All screenshots use fixture content. No microphone, provider session, or private desktop content was captured.

</details>

## Thoughts: quick notes and to-dos

<p align="center">
  <img src="screenshots/thoughts.png" alt="Notes inside the Side Chat drawer with the shared navigation and Peek controls; fixture content" width="32%">
  <img src="screenshots/workspace-todos.png" alt="To-dos in the same Side Chat drawer; fixture content" width="32%">
  <img src="screenshots/workspace-peek.png" alt="Peek controls with the same Chat, Notes, and To-dos navigation; fixture content" width="32%">
</p>

Choose **Notes** or **To-dos** beside **Chat** in the drawer's navigation.
Peek's controls use the same tabs. Everything opens in the same edge drawer,
with a shared app header, theme, window controls, and sliding tab highlight.
Switching sections preserves both your chat draft and unfinished notes.

The **Peek** button in the app header brings the companion alongside the drawer.
While enabled, Peek reacts to note capture and saving. Notes and to-dos also work
with Peek powered off and while a chat reply is running.

- **Notes:** type, then **Ctrl+Enter** to save. Click a note to edit it.
- **To-dos:** type, then **Enter** to add. Check it off; completed items fold
  into **Completed**, where you can uncheck them.
- **Voice:** click the microphone, speak, then stop. Review the transcript and
  save. The existing Voxtype daemon handles recognition; no agent is started.
- **Search:** press **Ctrl+K** or use the app-header magnifier to search notes, tasks, and conversations together. **Ctrl+F** filters the current Notes / To-dos list.
- **Delete:** hover a note or to-do and click ×. **Undo** brings it back.
- **Chat:** a message's lightbulb switches to a note draft. A note's chat icon
  returns to Chat with its text in the composer for you to review and send. Saved items and messages keep a clickable link to their source note or conversation.
- **Convert:** hover an item and choose the checkmark to turn a note into a task, or the pencil to turn a task into a note. Converting to a note clears completion and its reminder.

The drawer eases between content sizes, pages fade into place, and checked
to-dos fold out of the list. Peek's **Reduce motion** preference applies throughout.

Drafts recover across closing, changing tabs, and restarting. Notes remain plain
Markdown in `~/Documents/Thoughts`; an existing Omathought `notesDir` setting is
honored. To-dos add `kind: "todo"` and `done: true/false` frontmatter. Deleted
files remain in `.thoughts/trash` inside the notes folder; Undo is shown for seven
seconds. **Preferences → Recently deleted** restores notes, tasks, and conversations later. Nothing is automatically purged; conversations deleted before 1.15.0 cannot be recovered retroactively. Draft recovery lives
in Side Chat's state folder under `thoughts/drafts.json`. An external edit causes
a conflict message with **Save copy**, preserving both versions.

While Peek is listening, say **“Save this thought: …”**, **“Add a todo: …”**, or
**“Find my notes about …”**, or **“Show my to-dos”**. These run locally;
navigation and search open the corresponding workspace tab. Notes are separate from Peek's
memories and do not enter agent context unless you choose to discuss them.
Finish or pause one microphone recording before starting the other.

This desktop uses the **numpad** for Side Chat. **4 / 5 / 6** open Chat / Notes / To-dos.
**1 / 2 / 3** open those sections and start listening; tap again to stop.
Notes and To-dos keep the transcript as a draft for review. Use the regular
keyboard's **Ctrl+Return** to save. **Numpad Enter** remains system dictation:
hold to record, release to type into the focused application.
See the [complete keypad map and temporary homes for displaced shortcuts](docs/keypad.md).

`thoughtsNew` always opens a fresh note, and `thoughtsCaptureStart` always records
a note, regardless of the last tab. `thoughtsTodos` opens the To-dos tab.
The former F1 / Super+F1 / Super+F2 bindings have moved to the keypad.
Set `SIDE_CHAT_THOUGHTS_DIR` to use a different Markdown folder for development.

## Capture, find, and follow through

<p>
  <img src="screenshots/workspace-reminder.png" alt="A to-do with its exact reminder time previewed before saving; fixture content" width="32%">
  <img src="screenshots/workspace-search.png" alt="One search across notes, tasks, and conversations; fixture content" width="32%">
  <img src="screenshots/workspace-capture.png" alt="Selected text with Note, To-do, and Ask Peek actions; fixture content" width="32%">
</p>

### Reminders without a form

In **To-dos**, type **“Call Alex tomorrow at 3pm”**. Check the date and time shown
under the composer, then press **Enter**. The task saves as “Call Alex” with its
reminder. You can also use the bell to add or change a time on an existing task.

Supported examples: `in 20 minutes`, `tomorrow at 3pm`, `Friday at 9am`,
`2026-09-18 at 15:30`, and `at noon`. Dates use your local timezone; a date without
a time uses **9am**, and a bare hour from 1–7 means the afternoon. The preview
shows the actual choice before saving. Past times and invalid dates are rejected.
Use × beside the preview to remove the reminder.

Desktop notifications offer **Open task**, **Snooze 10 min**, and **Done**.
Reminders work with Peek off. Completed and deleted tasks stay quiet, and delivery
state survives app restarts. If the shell is closed or the computer sleeps,
overdue reminders arrive when it is running again. Notification action buttons
remain available for up to 24 hours; the task remains accessible in To-dos.

### Capture selected text

Select text in another application and run
`omarchy-shell blr.side-chat captureSelection`. The capture sheet opens
with **Note**, **To-do**, and **Ask Peek** actions. These prepare a draft for review;
Ask Peek uses the shared chat and never sends automatically. The source app is
shown when available. Your existing note and chat drafts are preserved.

Selection is read through accessibility or Wayland's primary selection before
opening the drawer. If an application does not expose its selection, copy the
text and choose **Use clipboard**. Capture does not synthesize Copy or overwrite
your clipboard. The Clipboard button in search explicitly reads copied text.

The [keypad configuration](deploy/side-chat-keypad.lua) uses physical keycodes
for this desktop's Magic Keyboard. On another keyboard, choose an unused binding
for `omarchy-shell blr.side-chat captureSelection` after checking your layout.

### One search, simple recovery

**Ctrl+K** inside the app searches saved note bodies, task bodies, conversation titles, and full
message text locally. The most relevant and recent 40 matches appear together.
Use **↑ / ↓**, then **Enter**, or click a result. **Esc** returns to the section
you came from with your draft intact. Searching never starts an agent.

**Preferences → Recently deleted** restores removed notes, tasks, and chats.
**Export workspace** saves a private `.zip` with Markdown, deleted items,
recoverable drafts, a consistent snapshot of the app databases, and saved
attachments. Pick a new filename; existing backups are never overwritten.
The archive includes restoration instructions. External agent session files,
agent credentials, and speech models are excluded, so this is a backup of this
workspace rather than a complete copy of your CLI agents.

## Your agent, without another terminal in the way

Move to the lower-left edge of either display and Side Chat peels into view. Leave it and the preview disappears; click it and it stays open. Replies keep running when the panel closes and a desktop notification tells you when one is ready. Short conversations stay compact, and long ones scroll naturally.

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

### Voice and computer control

- Uses the existing Voxtype daemon and Pocket TTS by default; optional local Parakeet, Kokoro, and legacy ASR engines are available.
- Offers wake phrase, hands-free follow-ups, barge-in, mute, stop, and device selection. Voxtype mode uses its existing daemon as Peek's single ASR process, avoiding a second multi-gigabyte Parakeet load.
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
- Internet access during setup; the CPU runtime and optional local speech models require several gigabytes

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

**Voxtype prerequisite:** shared streaming needs a daemon containing the upstream private-file-output fix. Updating Side Chat does **not** update your Voxtype daemon. Peek conservatively refuses the known-affected, unpatched `1.0.1` daemon before starting a recording. Use the [pinned-build instructions](docs/voxtype.md), or install and select the optional local Parakeet recognizer below. Setup reports this known compatibility problem; it does not silently replace your daemon.

With Peek powered off and no reply running:

```bash
cd ~/.config/omarchy/plugins/blr.side-chat
python3 setup.py --with-peek
python3 setup.py --check --with-peek
```

This installs the CPU speech runtime, Voxtype daemon integration, audio tools, accessible-app support, and isolated-browser tooling. It does not download Peek's bundled Parakeet model or turn on the microphone. Voxtype owns recognition by default, so the first setup avoids a second multi-gigabyte ASR load.

Native mouse and keyboard control, physical takeover detection, and the emergency **Ctrl+Alt+Esc** shortcut require the explicit desktop-input option:

```bash
python3 setup.py --with-peek --with-desktop-input
```

This installs named udev/module configuration and grants your active seat access to input and virtual-input devices. It does not run the agent as root or add your user to the `input` group. Log out and back in if the final device check asks you to.

Optional engines include `python3 setup.py --with-parakeet`, `python3 setup.py --with-kokoro`, and `python3 setup.py --with-legacy-asr`; all imply Peek setup. Parakeet is a local download/build for users who want Peek's wake phrase, silence endpointing, streaming partials, or device routing:

```bash
python3 setup.py --with-parakeet
python3 setup.py --check --with-parakeet
```

### 3. Recognition choices after first install

Voxtype is the default recognition backend. It keeps Peek's spoken replies and assistant controls while avoiding a duplicate ASR model. The explicit form is still accepted for scripts and existing installations:

```bash
cd ~/.config/omarchy/plugins/blr.side-chat
python3 setup.py --with-voxtype
python3 setup.py --check --with-voxtype
```

Open **Peek settings → Speech → Recognition → Model**, choose **Voxtype · shared daemon**, and apply. Peek starts Voxtype in private file mode and sends the finished transcript through the normal assistant queue; it never types into the focused application or overwrites your clipboard. Turn the Peek microphone on and off with the usual Peek keybinding.

Voxtype mode is **tap to start, tap again to send**—not hold-to-talk. With the example bindings below, tap Decimal, speak, then tap Decimal again; Peek transcribes the recording, sends it to your assistant, and speaks the reply unless muted. An existing Enter dictation binding stays unchanged. Finish one recording before starting the other; both share one daemon and recognition model. Peek refuses to start while Voxtype is already busy.

The input meter reads the daemon's existing audio-level stream; it does not open another microphone or load another recognition model. Older daemons without level telemetry can still transcribe, but will not show a live meter. Empty recordings show a notice instead of leaving the previous reply unexplained.

Wake phrase, automatic silence endpointing, and Peek's local microphone/device controls are unavailable in this mode because Voxtype owns capture. Configure Voxtype itself in `~/.config/voxtype/config.toml`. To keep the large model unloaded while idle, enable its on-demand mode and restart the daemon:

```bash
voxtype config set parakeet.on_demand_loading true
systemctl --user restart voxtype
```

To switch back to a downloaded local recognizer, run `python3 setup.py --with-parakeet`, then choose **Parakeet Unified** in settings. The legacy Zipformer + Whisper option is installed with `python3 setup.py --with-legacy-asr`. These downloads are optional and can be added later without reinstalling the plugin.

## Keybindings

Plugin setup does not automatically edit your keybindings. This desktop loads
[`deploy/side-chat-keypad.lua`](deploy/side-chat-keypad.lua) through
`~/.config/hypr/side_chat_keypad.lua`. Physical numpad **0** opens or closes Peek,
and **decimal (.)** toggles Peek's microphone, with Num Lock either on or off.

```lua
-- Peek: bare numpad shortcuts, with Num Lock on or off.
hl.unbind("code:90")
hl.unbind("code:91")
hl.unbind("KP_0")
hl.unbind("KP_Insert")
hl.unbind("KP_Decimal")
hl.unbind("KP_Delete")
o.bind("code:90", "Toggle Peek", "omarchy-shell blr.side-chat peek")
o.bind("code:91", "Toggle Peek microphone", "omarchy-shell blr.side-chat peekToggleMicrophone")
```

These physical keycodes match this desktop's Magic Keyboard. The full mapping
also clears previous bindings before assigning each key. To bind the chat drawer
to another unused key, use `omarchy-shell blr.side-chat toggle`.

The preferred desktop controls now live on the numpad:

| 7 · ChatGPT | 8 · Gemini | 9 · Higgsfield AI |
| --- | --- | --- |
| **4 · Chat** | **5 · Notes** | **6 · To-dos** |
| **1 · Chat + listen** | **2 · Notes + listen** | **3 · To-dos + listen** |
| **0 · Toggle Peek** | **. · Toggle Peek microphone** | **Enter · System dictation (hold)** |

Tap **1 / 2 / 3** once to open that section and start listening, then again to
stop. In Chat, Peek transcribes and handles the voice request as usual; Notes
and To-dos prepare drafts to review and save. The **.** key uses the same Peek
microphone as **1**, without opening the Chat drawer. Finish a recording before
switching voice destinations.

**Clear** hides the drawer; **/** stops work; **=** opens Peek controls.
**+ / − / \*** retain volume and play/pause. Old numpad launchers temporarily
use **Super + the same numpad key**. See [the complete map](docs/keypad.md).
**Ctrl+K** searches inside the app. History and Preferences remain accessible
in the header; the old F1 / Super+F1 / Super+F2 app bindings are removed.


**Numpad Enter** is **system dictation**: hold to record and release to type into
the focused application. **Super+Numpad Enter** is also available as an alias.
Use **.** or **1** to speak to Peek. Both share the existing Voxtype daemon with
system dictation, so finish one recording before starting another.

After editing bindings:

```bash
hyprctl reload
hyprctl configerrors
```

The second command should report no errors.

## Use

Move the pointer into the bottom 160 scaled pixels of the left screen edge. Click to pin the panel open; use Escape, Close, or click outside to dismiss it. While Peek is on, edge hover is off so it cannot fight with dragging him; open chat from Peek's controls or your keybinding instead.

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
| `omarchy-shell blr.side-chat toggle` | Open or close the workspace |
| `omarchy-shell blr.side-chat open` | Open the workspace at its current section |
| `omarchy-shell blr.side-chat newChat` | Start a conversation |
| `omarchy-shell blr.side-chat peek` | Open or close Peek |
| `omarchy-shell blr.side-chat peekToggleMicrophone` | Toggle Peek's microphone |
| `omarchy-shell blr.side-chat companionControls` | Open Peek controls |
| `omarchy-shell blr.side-chat thoughts` | Open or close Notes / To-dos in the shared drawer |
| `omarchy-shell blr.side-chat thoughtsNew` | Open a new note draft |
| `omarchy-shell blr.side-chat thoughtsTodos` | Open To-dos |
| `omarchy-shell blr.side-chat thoughtsCaptureStart` | Start recording a note |
| `omarchy-shell blr.side-chat thoughtsCaptureStop` | Stop recording and transcribe into a draft |
| `omarchy-shell blr.side-chat thoughtsCaptureCancel` | Cancel note recording |
| `omarchy-shell blr.side-chat captureSelection` | Capture selected text before opening the drawer |
| `omarchy-shell blr.side-chat workspaceSearch` | Open or close shared search |
| `omarchy-shell blr.side-chat keypad ACTION` | Run a keypad action: `chat`, `notes`, `todos`, `listen-chat`, `listen-notes`, `listen-todos`, `note`, `selection`, `search`, `workspace`, `history`, `settings`, `peek`, `microphone`, `record`, `record-stop`, `stop`, `hide`, `controls` |
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
sleep 2
omarchy-shell blr.side-chat open
```

The updater only works on Git-managed installs. If it says the plugin is not a
Git checkout, migrate the legacy copy install (Omarchy moves it to a backup):

```bash
omarchy plugin remove blr.side-chat --yes
omarchy plugin add https://github.com/baileyrosen3/side-chat.git --enable --yes
cd ~/.config/omarchy/plugins/blr.side-chat
python3 setup.py
omarchy restart shell
sleep 2
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
- Thoughts uses local Markdown files and recoverable drafts. Notes enter agent context only when you choose to discuss them; recording a note does not send it to an agent.

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
<summary><strong>Voxtype mode cannot start or stays recording</strong></summary>

Confirm the daemon is running with `systemctl --user status voxtype` and that `voxtype status` responds. Peek's Voxtype mode records until you toggle its microphone off; it does not use the bundled wake phrase or silence endpointing. If you want those behaviors, switch Recognition to **Parakeet Unified** and run setup with `--with-parakeet`.

</details>

<details>
<summary><strong>Peek listens, but Voxtype types into the focused window</strong></summary>

Voxtype 1.0.1's streaming path ignores the recording's `--file` override. A correct Peek microphone binding can therefore still type into another app and return an empty transcript. This is a daemon bug, not a keybinding problem. Streaming requires a Voxtype build containing the [upstream file-output fix](https://github.com/peteonrails/voxtype/blob/320a737e5d3c8662e0ec7de95f75407baa784d82/src/daemon.rs#L1187), followed by a daemon restart. The released 1.0.1 binary does not contain it. Alternatively, use Peek's optional local recognizer.

Custom Voxtype overlays must also honor the daemon's `osd_suppressed` marker to hide during Peek recordings. An overlay appearing alone does not establish where the transcript was delivered.

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

The original Side Chat source remains under the [MIT license](LICENSE). Peek's interface, integration, and original procedural 3D companion are under [GPL-3.0-or-later](COPYING.PEEK); distribute the combined plugin under GPL-3.0-or-later while preserving the MIT notices.

Runtime dependencies, model licenses, voice attribution, and pinned revisions are documented in [THIRD_PARTY.md](THIRD_PARTY.md). The companion uses original procedural geometry and shaders—there are no purchased or downloaded character assets.
