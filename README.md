# Side Chat for Omarchy

An edge chat for Omarchy with persistent coding-agent conversations and an optional local voice companion. Move to the bottom-left screen edge to open it; the interface follows your Omarchy theme.

- Chat with your existing OMP, Pi, Codex, or Claude session, including native tools and permission prompts.
- Stream replies, attach files and images, search saved conversations, and continue in a terminal.
- Add local speech recognition, spoken replies, and the Peek robot with Peek setup.
- Use desktop or isolated browser control, with visible actions and a stop control.

Plugin ID: `blr.side-chat`. Code and model attribution: [THIRD_PARTY.md](THIRD_PARTY.md).

## Install

Requires **Omarchy with the Quickshell plugin system (Quattro)** in a Hyprland desktop session. Older Waybar-based releases are not supported. Peek's pinned binaries currently support **Linux x86_64**. Speech models and CPU dependencies take several GB and require internet access during setup; inference runs locally afterward.

### Chat

Run these commands in your normal desktop terminal:

```bash
omarchy pkg add python git
omarchy plugin add "https://github.com/baileyrosen3/side-chat"
```

If Omarchy asks whether to enable it now, choose **No** until dependencies are ready. Then:

```bash
cd ~/.config/omarchy/plugins/blr.side-chat
python3 setup.py
omarchy plugin enable blr.side-chat
omarchy-shell blr.side-chat open
```

`setup.py` installs missing packages through `omarchy pkg add`, including Qt Quick 3D and clipboard support. Qt Quick 3D is required even for chat because the plugin imports companion components. Run setup without `sudo`; the package manager requests privileges when needed.

You need one installed, authenticated default agent. If setup reports that none is available, choose one through **Setup → Default Agent**, or run, for example:

```bash
omarchy default agent omp
```

Omarchy installs/selects that agent and opens its terminal. Complete the agent's provider sign-in there, then rerun `python3 setup.py --check`. OMP, Pi, Codex, and Claude support native sessions and Peek; other supported CLIs provide the fallback chat mode described below. Keep an existing agent if it already works. Side Chat uses its credentials and provider billing.

### Add voice and computer control

Run inside the installed plugin directory, with Peek powered off and any active reply finished:

```bash
python3 setup.py --with-peek
python3 setup.py --check --with-peek
```

This installs the CPU speech runtime, builds the pinned Parakeet adapter, downloads the required models and verified agent-browser binary, and installs the system tools below. A complete existing Voxtype Parakeet model is reused. Voxtype itself is optional. Setup prepares the Pocket voices for offline use; it never starts the microphone. Open Side Chat and select **Peek** when ready.

For native desktop input, including physical takeover detection and **Ctrl+Alt+Esc**, also run:

```bash
python3 setup.py --with-peek --with-desktop-input
```

The input option installs two named system configuration files, loads `uinput`, and applies active-seat access to keyboard, mouse, touchpad, and virtual input devices. This lets applications running as your user read input events and inject input. It does not add you to the `input` group or run agents as root. If the final check still reports unavailable devices, log out and back in, then rerun the same command with `--check`. Input permissions supplied by an existing setup can be checked with that command without installing any rules.

Optional speech engines:

```bash
python3 setup.py --with-kokoro
python3 setup.py --with-legacy-asr
```

These flags include Peek setup. Select the installed engine in **Preferences → Peek → Speech**.

### Optional Peek keybindings

Side Chat does not install or replace keybindings. The maintainer uses the physical numpad 0 key to open or close Peek and numpad decimal to toggle Peek's microphone. Add these exact bindings to `~/.config/hypr/bindings.lua`:

```lua
-- Peek: bare numpad shortcuts, with Num Lock on or off.
o.bind("KP_0", "Toggle Peek", "omarchy-shell blr.side-chat peek")
o.bind("KP_Insert", "Toggle Peek", "omarchy-shell blr.side-chat peek")
o.bind("KP_Decimal", "Toggle Peek microphone", "omarchy-shell blr.side-chat peekToggleMicrophone")
o.bind("KP_Delete", "Toggle Peek microphone", "omarchy-shell blr.side-chat peekToggleMicrophone")
```

`KP_0`/`KP_Insert` are the same physical key in the two Num Lock states; so are `KP_Decimal`/`KP_Delete`. To bind the chat panel instead of Peek, use `omarchy-shell blr.side-chat toggle` with any unused key. After editing bindings, run `hyprctl reload` and `hyprctl configerrors`; the second command should report no errors.

### What setup installs

| Feature | System dependencies |
| --- | --- |
| Chat and companion UI | Python, Qt Quick 3D, wl-clipboard |
| Speech and build tools | uv, a working Rust/Cargo toolchain, base-devel, libsndfile |
| Audio and echo cancellation | PipeWire, pipewire-audio, pipewire-pulse, WirePlumber, libpulse |
| Browser and native control | Chromium, grim, wtype |
| Accessible app controls | python-gobject, at-spi2-core |
| Local volume, brightness, media commands | WirePlumber, brightnessctl, playerctl |

Existing working `uv` and Rust executables are reused. Python speech packages are installed in `~/.local/share/side-chat/runtime`, models in `models/`, helper binaries in `bin/`, and Cargo output in `build/` under that same data directory. Pocket weights and voices use the Hugging Face cache. `XDG_DATA_HOME` or `SIDE_CHAT_DATA` can relocate Side Chat's data; use the same environment for setup and the running shell.

## Update, disable, and remove

Finish any reply and power Peek off before updating:

```bash
omarchy plugin update blr.side-chat --yes
cd ~/.config/omarchy/plugins/blr.side-chat
python3 setup.py
```

`--yes` updates this trusted plugin without printing the review diff or asking for confirmation. Omit `--yes` when you want to inspect changes first; Omarchy will print the incoming Git diff and ask you to confirm. That diff is terminal output, not a file or an error.

Confirm that the checkout, manifest, and running UI agree after an update:

```bash
git -C ~/.config/omarchy/plugins/blr.side-chat log -1 --oneline
jq -r .version ~/.config/omarchy/plugins/blr.side-chat/manifest.json
omarchy-shell blr.side-chat status | jq -r '.uiVersion, .uiSource'
```

The two version values should match, and `uiSource` should point inside `~/.config/omarchy/plugins/blr.side-chat`. The same version is visible at the bottom of **Preferences**. If you use Peek, run `python3 setup.py --with-peek` instead, adding your optional engine flags. Omarchy add/update does not run dependency installers; setup is an explicit step. The checkout and its Git metadata remain intact for future updates. This follows the same Git installation approach as [Enhanced Agents](https://github.com/baileyrosen3/omarchy-agents) and [Omarchy's plugin reference](https://github.com/omacom/omarchy/blob/quattro/shell/README.md).

```bash
omarchy plugin disable blr.side-chat
omarchy plugin enable blr.side-chat
omarchy plugin remove blr.side-chat
```

Disable stops the service until enabled again. Remove deletes the plugin checkout. Chat history, attachments, speech models, and runtime remain available for reinstalling. History is in `~/.local/state/omarchy/side-chat`; the speech runtime and downloads are in `~/.local/share/side-chat`. Delete those directories manually only if you also want to erase that data. Shared Voxtype models and Hugging Face caches may be used by other applications.

If you installed Side Chat's desktop input rules and want to remove them:

```bash
sudo rm /etc/udev/rules.d/70-side-chat-input.rules /etc/modules-load.d/side-chat-input.conf
sudo udevadm control --reload-rules
```

Reboot to clear existing device access. Other applications' input rules may still grant access. Shared Arch packages are left installed.

If an older copy install already occupies `blr.side-chat`, back up that folder, remove the plugin with Omarchy, and use `plugin add` for a Git-managed installation. `install.py` is for development copy installs and refuses to replace Git checkouts.

## Troubleshooting setup

- **Unknown `omarchy plugin` command:** this needs Omarchy's Quickshell plugin system.
- **Missing packages or runtime files:** rerun `python3 setup.py --check`, adding the same voice/input flags you installed. Checks do not download files, start the microphone, or send an agent request.
- **Agent unavailable or authentication failed:** open its terminal, sign in, and check **Setup → Default Agent**. Dependency checks find the executable; they do not verify an account.
- **No sound or microphone:** check the default devices in Omarchy's audio settings and `pactl info`. Peek settings offer device selection. Setup does not replace your audio routing.
- **Desktop clicks or takeover unavailable:** use `--check --with-desktop-input` from the active local desktop session. Browser mode can use isolated Chromium without native input access.
- **Interrupted model download/build:** rerun setup with the same flags. Completed verified downloads are reused.
- **Update only showed a Git diff:** the diff is Omarchy's review output, not a downloaded file. Confirm the update at the prompt, or rerun `omarchy plugin update blr.side-chat --yes`.
- **Old UI after update:** compare the manifest and live versions with the commands above, then run `omarchy-shell shell rescanPlugins`. If the plugin folder has no `.git` directory, follow the older-copy migration note above. Keep Peek off during dependency updates.

## Use

Move the pointer to the bottom 160 scaled pixels of the left edge on either monitor. The whole chat peels out; move away to dismiss the preview. Clicking or typing keeps it open until Escape, Close, or a click outside. It continues generating while closed.

The compact header shows the conversation name and controls for History, New Chat, width, Preferences, and Close. Subpages replace those controls with a clear Back action. Peek and Terminal sit beside the working folder below the composer. Hover a message to copy, edit, or retry it. Code blocks have a separate copy control. Settings contain model and thinking overrides, the working folder, conversation rename, and Markdown export. New conversations follow `~/.config/omarchy/defaults/agent`; existing ones retain their original agent. The active default is checked every three seconds.

The interface pairs a rounded, screen-connected outer outline with compact neo-brutalist controls: square fields, flat fills, hard shadows, and uppercase navigation. A crisp offset shadow follows the outer silhouette in your theme’s accent color. Colors come from your active Omarchy theme, including readable text on accent fills, and update live with theme changes. Short conversations fit their content; longer conversations scroll. Settings, history, permissions, and Peek use the same controls.

**Preferences → Window outline** is on by default and saves immediately. The outline follows Hyprland’s active window border colors, opacity, width, and gradient. Keyboard focus keeps a visible outline when the option is off; **Reset** turns it back on. Appearance preferences are separate from agent settings and can change during a reply.

| Shortcut | Action |
| --- | --- |
| Enter | Send |
| Shift+Enter | New line |
| Ctrl+N | New conversation |
| Ctrl+H | History |
| Ctrl+Shift+V | Paste an image from the clipboard |
| Ctrl+Shift+C | Copy the last message |
| Escape | Dismiss the panel |

You can also use `omarchy-shell blr.side-chat toggle`, `open`, `close`, `newChat`, or `status`. `openOnScreen DP-1` targets a monitor. No keybindings are overwritten.

For voice mode, `omarchy-shell blr.side-chat peekOnScreen DP-3` enables Peek on that display, `companionControls` opens its controls, and `peekSettings` opens advanced settings. `omarchy-shell blr.side-chat microphone ""` selects the system-default input; a PipeWire source name selects a specific microphone. Selecting an input does not itself enable listening.

For keyboard access, `peek` toggles Peek on or off without reopening chat when he turns off. `peekOpen` only opens him, and `peekToggleMicrophone` toggles his microphone (starting Peek if needed). The microphone toggle preserves your hands-free and wake-word preferences. See **Optional Peek keybindings** above for the maintainer's exact numpad bindings.

## Chat behavior

- Streaming replies where the CLI supports them; selectable Markdown and fenced code.
- Stop aborts the native agent turn and preserves a partial reply; the idle session remains available. Unresponsive agents and legacy requests are terminated with their process groups.
- Conversation history, search, rename, delete, drafts, edit-and-retry, and export.
- Text/code files, image attachments, file drop, and clipboard image paste via `wl-paste`.
- Attachments are copied when sent so follow-up context doesn't change when the original file changes.
- Model and reasoning overrides are optional; blank/default keeps the agent's own configuration.
- Long replies scroll independently. Scrolling up pauses automatic scrolling until you return to the bottom or choose Latest.

## Peek mode

Select **Peek** in the panel, or run `omarchy-shell blr.side-chat peek`. Peek peeks around the left edge, with a rounded shell, a bent antenna, a smiling face, and articulated fingers gripping the edge. Hover to make it lean into view and reveal controls; click for more controls, or drag vertically to save its position. The controls stay visible while you move onto the panel and hide shortly after you leave both it and Peek. When chat opens, it peeks around the panel’s edge. Its shell uses the live theme foreground. Its eyes, trim, antenna, and face tint change together with the current expression, using a palette derived from the live theme accent; errors use the urgent color. Neutral lighting preserves those hues, and theme changes update every material. Its face tracks your pointer, raises a brow when curious, smiles and waves to greet you, squints while thinking, celebrates completed work, and animates spoken replies.

Peek follows the mouse across the desktop, including other monitors; hovering is only needed to reveal controls. One small cursor worker queries Hyprland at most eight times per second, backing off when idle or the compositor is slow. Each request connects, sends, and closes independently of Quickshell's UI thread so rendering delays cannot hold up the compositor's synchronous control socket. Replies have a 200 ms deadline, and output backpressure pauses polling. Turns use a damped spring at up to 60 Hz, dropping to 30 Hz for idle motion. Unchanged coordinates do not update the rig. The worker stops when Peek is hidden, off, in standby, reduced motion, or expression strength is zero.

Open **Peek settings → Companion → Appearance** to preview 19 expressions and adjust expression strength or reduced motion. The appearance preview cannot start speech or an agent. Reduced motion freezes ambient motion, cursor tracking, and gestures while still showing static state expressions. The alternative companions are parked under `dev/companion-concepts/` and are not loaded or installed.

**Robot design rule:** derive character colors from Omarchy’s live `Color` roles. The shell keeps its theme foreground, while expression hues rotate relative to the theme accent and errors follow the urgent color. Do not cache a palette at startup. Shape, lighting, and facial motion keep Peek recognizable across themes.

The floating controls offer microphone, stop, conversation, spoken-reply mute, Desktop/Browser, settings, standby, and power. Escape dismisses the controls. **Conversation** opens the existing chat beside the companion. Closing that panel leaves Peek running. Turning the microphone off stops capture and immediately finalizes your current phrase for sending, without waiting for silence; local recognition still needs time to finish. Leaving the microphone on uses the pause duration and adaptive pause settings. Toggling the microphone alone preserves the spoken reply; a submitted phrase follows the interruption setting. Standby returns to “Hey Jarvis” listening when enabled, and **power** shuts Peek down. With wake listening disabled, standby pauses the microphone. Peek does not start automatically at login. Error and transcript captions open the conversation when clicked.

Advanced settings remain available from **Preferences → Peek · voice and control settings**, even while Peek is off. Speech, Listening, Control, and Companion tabs include models, model folder, CPU threads, streaming profile, voices, volume, Kokoro pace, endpoint timing, speech sensitivity, maximum utterance length, interruption, echo cancellation, devices, control mode, reduced motion, personality, and local memory/routines/watches. Changes are validated and applied together; model changes reload the voice worker when the agent is idle. Chat keeps native CLI actions, attachments, history, edit/retry, and terminal handoff.

Speech defaults to resident Parakeet Unified English 0.6B for streaming captions and final recognition, with streaming Pocket TTS for spoken replies. It reuses an existing Voxtype Unified ONNX model folder without copying or downloading it again. The same model stays loaded through each utterance. Fast recognition is the default, with 320 ms chunks and a 450 ms base hands-free pause before sending. Balanced uses 560 ms chunks and More context uses 1,120 ms. These are chunk sizes, not total response times. Zipformer + Whisper remains an optional legacy engine. Optional Kokoro supports Heart, Bella, and Michael voices plus speaking pace; Pocket offers Alba, Marius, Javert, Fantine, Éponine, Azelma, Charles, Mary, and Peter at each voice’s natural pace. Use Speech → Preview voice to audition a selection before applying it; an explicit preview plays even when replies are muted. Apply an engine change before previewing its voices. Preview never enables the microphone or starts an agent. Echo cancellation uses a temporary PipeWire module that is removed when Peek is turned off; raw microphone recordings are not saved. The model workers run separately from the shell and load from a private local runtime. No cloud speech API or additional account is needed. Your CLI retains its own configured model/provider, including any existing costs.

Peek starts a brief acknowledgment after about a quarter-second if the agent has not begun speaking. It prepares that cue during voice warmup, streams completed sentences and natural clauses early, and gives occasional spoken updates during longer tasks. Updates reflect observed tool activity or elapsed waiting, never private reasoning. Real replies replace queued progress cues immediately; stopping, muting, interrupting, or completing the task clears stale cues. Turn off **Speech → Quick acknowledgment & progress updates** to keep replies only. Existing custom listening settings are preserved when updating.

Peek adds `jarvis_computer` through the native OMP/Pi extension API and a private stdio MCP server for Codex and Claude. It can observe displays, focus windows, move/click/drag/scroll, type Unicode, use shortcuts, and operate websites in either the visible default Omarchy browser or an isolated headless Chromium through agent-browser. The theme-colored AI marker shows native pointer actions; isolated browser actions retain an in-page AI marker for observation. Screenshots carry frame identities and coordinate transforms, and stale window/display geometry is rejected. Existing file, shell, skill, and permission behavior remains available.

**Desktop** controls your current apps and opens URLs through `omarchy launch browser`, preserving your configured default browser and normal profile. Further web interaction uses native screenshots, mouse, and keyboard. The broker rejects headless DOM commands in this mode, and OMP/Pi extensions block their built-in browser route while Peek is active. Every supported agent receives the current mode on each turn. Desktop shares input with you. Moving the physical mouse or pressing a key pauses active native input. **Browser** restricts the supplied computer tool to an isolated **headless** Chromium session whose DOM input does not use your hardware pointer. Switching back to Desktop or closing the controller closes that browser session. This is an independent browser, not a separate complete Linux desktop or a filesystem sandbox. Unrestricted CLI shell tools can operate outside the supplied controller.

Use the Stop button or **Ctrl+Alt+Esc** to stop speech and queued computer actions and interrupt the current agent turn. An input event already delivered to an application cannot be undone. Permission questions stay visible; voice can answer an active Yes/No or exact-choice prompt, while ambiguous answers leave it pending. Code blocks and tool output are not read aloud.

Additional installation for local voice and computer control:

```sh
# Run inside ~/.config/omarchy/plugins/blr.side-chat
python3 setup.py --with-peek --with-desktop-input
```

The setup uses `uv` to create a Python 3.12 runtime under `~/.local/share/side-chat/runtime`, downloads pinned models under `~/.local/share/side-chat/models`, and installs a verified agent-browser binary under `bin/`. It builds a small pinned Rust adapter for Parakeet using Cargo.lock and ONNX Runtime. Existing Voxtype models are preferred; otherwise setup downloads the pinned Unified export. `--with-legacy-asr` installs Zipformer/Whisper and `--with-kokoro` installs optional Kokoro. Pass these flags to the root `setup.py`. Pocket TTS uses the local Hugging Face cache; runtime inference is offline. Chromium, PipeWire utilities, `pactl`, `grim`, `wtype`, and access to `/dev/uinput` are required for their corresponding features. It does not make the agent run as root. See [THIRD_PARTY.md](THIRD_PARTY.md) for code/model/voice licenses and attribution.

On this Ryzen AI 9 HX 370, synthetic sample tests measured Pocket's first audio chunk at 80–120 ms and the resident Parakeet adapter loaded the existing 2.4 GB model in about 2.1 seconds. These are component measurements, not a promise of end-to-end response time: the chosen CLI/model and microphone conditions also matter. `tools/voice_live_check.py` validates the full audio-to-CLI-to-speech path using virtual PipeWire devices without recording room audio. Native click/Unicode typing and physical takeover were exercised on a disposable GTK window; the headless browser passed fill/click/marker checks without opening a desktop window. A real OMP turn opened Google in the configured Zen browser and verified a desktop screenshot. Both Parakeet/Pocket push-to-talk and Parakeet/Kokoro hands-free paths were exercised with virtual audio. Room echo cancellation, acoustic interruption, and long-session reliability still need everyday use validation.

## Native CLI sessions

OMP (Oh My Pi), Pi, Codex, and Claude run as persistent native sessions behind the same chat UI. OMP/Pi use RPC, Codex uses app-server, and Claude uses its bidirectional stream protocol. Their normal coding system prompt, tools, skills, extensions, project instructions, account, and permission configuration remain enabled. The agent can read and edit files and run shell commands. Follow-ups go to the existing session without replaying a synthetic transcript. Existing text-only conversations migrate on their next message, preserving the visible history.

Each reply has expandable tool activity with commands, arguments, results, and completion/error states. CLI confirmation, selection, and text-input requests appear above the composer. By default, approval requests have **Allow** and **Deny** and follow the CLI's existing policy.

Click the shield and current access mode above the composer, or type **`/permissions`**, to choose a mode for the current conversation. The selector also lives in Preferences. Choices save automatically and apply to the next message; finish or stop the current reply before changing them. The existing native session is resumed with the selected policy. New conversations start at their default, and changing the agent or working folder before the first message clears the choice. Global CLI configuration is never edited.

| CLI | Side Chat choices |
| --- | --- |
| Codex | CLI default, Read-only, Workspace, Auto review, Full access |
| Claude | CLI default, Ask, Accept edits, Plan, Auto, Bypass permissions, Don't ask |
| OMP | CLI default, Ask, Allow writes, YOLO |
| Pi | CLI default, Ask before tools |
| OpenCode | Chat only, Auto approve |

Codex combines native sandbox and approval policies; Auto review keeps the workspace sandbox and routes escalation requests to Codex's reviewer. Full access disables the command sandbox and approvals. Claude Auto uses its classifier and requires availability for the current account/model; Bypass is a separate choice. OMP honors per-tool rules in all three explicit modes. Pi has no built-in approval mode, so **Ask before tools** loads a bundled extension that confirms each tool call; the adapter verifies it loaded before sending a prompt. This adds approval prompts, not a sandbox. Existing extensions remain enabled. These mappings follow the [official OpenAI documentation](https://learn.chatgpt.com/docs/app-server), [Claude permission modes](https://code.claude.com/docs/en/permissions), and [OMP approval modes](https://github.com/can1357/oh-my-pi/blob/main/docs/approval-mode.md).

OpenCode retains its text adapter: Chat only disables tools, while Auto approve uses native `run --auto` and preserves configured deny rules. Completed tool calls and failures appear in reply activity. Inline approval questions, native session handoff, and plan/build switching for OpenCode need a future native adapter. Other CLIs do not show modes yet. Unsupported CLI flags, account restrictions, and managed policy errors are surfaced by the CLI when the next message starts; Side Chat does not retry with broader permissions.

The selected native mode is also passed to terminal handoff. When returning, Side Chat reapplies its saved selection. Switching to CLI default restores Codex's resolved default approval policy, rather than inheriting an earlier session override. Selecting any mode clears **Always allow Bash** so the old Side Chat override cannot silently change the chosen behavior.

For Claude and Codex, a Bash/shell approval also offers **Always allow Bash**. It approves the waiting command and automatically answers future Bash command approvals in this conversation. The choice survives reopening Side Chat; new conversations start with **Ask**. Change it under **Preferences → Bash approvals**, or click **Bash: always** beside the composer to return to asking immediately. Settings save automatically and can be changed during a reply. Changing the working folder or the agent before the first message resets the choice.

This is a Side Chat conversation setting. It sends ordinary one-time approvals and does not write permission rules into the CLI's global/project configuration or change terminal handoff permissions. Bash commands can modify files and run programs. File-edit tool requests, MCP approvals, managed network approvals, extra permission profiles, and agent questions remain explicit. OMP/Pi extension prompts keep their existing behavior because their generic confirmation messages do not reliably identify Bash approvals.

Click **Terminal** below the composer to continue that exact saved session in Omarchy's configured terminal. Handoff is available after the first prompt, while the agent is idle. The panel releases its agent process before the terminal takes ownership; an exclusive file lock prevents both interfaces from writing to the same session. Exit the agent in the terminal to return to the panel; terminal messages and tool activity sync back automatically. The panel continues to work if hidden, and a terminal session survives a shell reload.

Edit and Retry branch the native conversation before the selected prompt. Existing file changes are not undone, and retrying an action may execute it again. Native sessions retain their original working folder; choose a folder in a new conversation to start elsewhere. Model and thinking settings can still change. The CLI manages context compaction. RPC-compatible slash commands are passed through; terminal-only interfaces remain available in the terminal. Switching to an unrelated session inside the terminal is outside the handoff contract.

Native session and Peek support covers **OMP, Pi, Codex, and Claude**. OpenCode and the other defaults retain their text adapters until their own native protocols are integrated. In CLI default mode, Codex follows its configured permissions; the explicit Read-only preset disables command escalation. External MCP tools retain their own permissions. MCP login/forms beyond simple confirmations can be completed in the terminal. Claude single-choice questions are supported; multi-select questions ask the agent to use individual choices instead.

Adapters cover OMP, Pi, Claude, Codex, OpenCode, Gemini, Copilot, Crush, and Grok. OMP, Codex, and Claude were verified with installed accounts: reading, editing and verifying a disposable config, calling Peek windows, and resuming native history. Native branching was verified with Codex and Claude, including removal of the retried turn and preservation of the original session file. OMP terminal handoff was exercised in the configured terminal; Pi and the handoff ownership protocol have subprocess coverage. Other adapters use documented or installed CLI command formats and parser fixtures; they have not all been authenticated and exercised end to end. Grok returns its final JSON answer; Codex/OpenCode may emit complete text blocks rather than individual tokens. Missing login, unavailable models, and command errors are shown in the conversation.

Images are supported through OMP, Pi, Claude, Codex, and OpenCode adapters, subject to the selected model's capabilities. Other adapters accept text attachments. Files must be text/code/Markdown or PNG/JPEG/WebP/GIF; arbitrary binary files and PDFs are rejected clearly. Limits: 8 attachments per message, 10 MB per file, 100,000 characters per text file or message. OMP/Pi RPC prompts, including encoded images, must fit within 1 MB; larger images can be supplied as local file paths for the agent's tools. Legacy transcript adapters have a 350,000-character context limit.

## Peek companion capabilities

Open **Settings → Peek · voice and control settings**. The same controls are available from the companion’s floating settings button.

- **Listening → Wake phrase** enables the local keyword model. The installed detector is trained for “Hey Jarvis”; renaming the companion to Peek does not retrain it. Turn on Peek once; use standby to wait for the keyword. Say “Hey Jarvis”, wait for the short chime in standby, then speak. Wake mode also requires that phrase before interrupting a running task or spoken answer; idle follow-ups remain available during the follow-up window. A configurable 5–60 second follow-up window stays open after speech/tasks. “Go to sleep” or “Sleep Peek” returns to standby; use the microphone or power controls to stop listening. Wake listening is off by default and does not start automatically after login.
- **Control → Screen context** chooses off, on-request, or every Desktop request. On-request recognizes references such as “this”, “that”, “my screen”, and “selected”. The active app’s title and optional screenshot/selected text go to the chosen agent/provider. No background screenshot recording or clipboard history is used. Screen images require an image-capable agent model; selection requires the app’s accessibility interface.
- **Companion → Memory** edits explicit saved preferences. Say “remember that I prefer compact windows”, “what do you remember”, or “forget I prefer compact windows”. Memory is private local SQLite, persists across conversations, and can be excluded from agent context in Control settings.
- **Fast local commands** handle volume, brightness, mute, music, terminal/browser/Files launches, workspaces, and explicit web URLs without an LLM round trip. Examples: “set volume to 30”, “pause music”, “open Google”, “switch to workspace 2”. Browser mode keeps web commands in isolated Chromium and refuses host app commands. Other requests use the existing default CLI session.
- **Corrections** can be spoken or typed while a task runs. Desktop input pauses at speech onset. OMP/Pi steering and Codex turn steering preserve the active task; unsupported adapters interrupt and continue the same saved session with the correction. Already completed file/shell actions are retained. A shell command already running may finish before the correction takes effect. “Stop” cancels the task instead.
- **Companion → Routines** names sequences of supported local commands, editable one per line. Say the routine’s name to run it. **Watches** adds timers or watches a user-owned process ID until it exits, with desktop notification and an idle Peek voice announcement. Timers and watches persist across shell reloads; notification delivery requires the shell to be running. Process exit does not establish successful completion. Watches are explicit, never automatic application surveillance.
- **App controls** expose AT-SPI semantic targets to the native agent, with stale-target checks, target highlight, and screenshot/native-input fallback for apps without an accessible tree. The tracked `config_read` / `config_write` tools verify small existing user config files and record restore points. **Companion → Undo** or “undo your last config change” restores them only if there are no newer edits. Normal CLI edits and desktop actions are not automatically undoable.
- **Buddy** shows real activity, looks toward accessible action targets, reacts to completion, and uses live microphone/playback levels. Control settings choose concise/balanced/lightly witty speech, expression strength, and reduced motion.

Memories, routines, watches, recent local activity, and tracked config backups live in `companion.sqlite3` beside chat history. No additional account or paid speech service is required. Your existing CLI/provider terms still apply. Speech model and code licenses are listed in THIRD_PARTY.md.

## Storage and privacy

History and preferences are stored in `~/.local/state/omarchy/side-chat/chats.sqlite3`, with attachment snapshots in `attachments/`. The directory is private (0700). Credentials stay with the selected CLI. Prompts and attached contents are sent to that CLI's configured provider. No web server, shared port, or remote chat database is used.

OMP/Pi native CLI files and all terminal ownership records live in `sessions/<chat-id>/` under the private state directory. Codex and Claude retain their native files under their own configured session directories; the chat stores a reference to them. `SIDE_CHAT_STATE` can point the bridge at an isolated test directory. Deleting a conversation removes its database row; attachment snapshots and native session files currently remain on disk. Export writes plain Markdown to the location selected in the file picker.

## Development and verification

```sh
python3 -m unittest discover -s tests -v
ln -s /usr/share/omarchy/shell/Commons Commons
quickshell --no-duplicate -p shell.qml
```

`Commons` is a development-only import link and is not installed. The production plugin runs inside Omarchy's existing shell. Backend tests exercise real subprocess pipes with local fixtures: Unicode streaming, stderr backpressure, persistent RPC sessions, native branching, permission responses, cancellation, terminal handoff/return, exclusive ownership, large RPC frame validation, legacy migration, attachment snapshots, default-agent changes, and export/deletion. The development copy installer uses fresh component paths for each build and verifies the loaded UI version, avoiding stale nested QML without restarting the shared shell or its lock screen. Git installations use Omarchy's normal plugin reload. See [implementation notes](docs/implementation.md) for the development history and [publishing](docs/publishing.md) for release preparation.

Protocol references: [OMP events](https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md), [Gemini headless mode](https://geminicli.com/docs/cli/headless/), [Grok headless mode](https://docs.x.ai/build/cli/headless-scripting). Other CLI flags were checked against installed help.

Companion checks: `python3 -B tools/wake_live_check.py` uses virtual audio for real keyword → Parakeet → local command → TTS and follow-up expiry; `tools/steer_live_check.py` tests a real OMP correction during a fixture command; `tools/companion_live_check.py` checks real GTK accessibility and tracked config restore. When the desktop is locked, the latter injects only the disposable fixture’s focus metadata and reports that compositor focus was not verified. Do not run voice fixtures concurrently because they share virtual device names.

Visual preview: `quickshell -p DesignPreview.qml` uses fixture messages with no microphone or agent connection. It includes both the screen-edge chat and peeking companion, explicitly labeled **Preview · no mic**. Close it with `quickshell -p DesignPreview.qml kill`.

Robot rendering checks (Qt 6, with a graphical session):

```sh
QT_QPA_PLATFORMTHEME=generic QT_QUICK_CONTROLS_STYLE=Basic QT_QUICK_BACKEND=rhi QSG_RHI_BACKEND=opengl /usr/lib/qt6/bin/qmltestrunner -input tests/qml -import tests/qml/imports -v1
```

The original neutral studio light probe is reproducible with `python3 tools/build_companion_lighting.py`. It adds no downloaded art or runtime dependency.

Speech timing and cancellation check: `~/.local/share/side-chat/runtime/bin/python -B tools/speech_latency_check.py` measures acknowledgment PCM in a virtual PipeWire sink, auditions all nine local Pocket voices, checks cancellation, and verifies the microphone stays off. It does not invoke an agent or use the room microphone.

Conversation audit and rationale: [docs/speech-audit.md](docs/speech-audit.md). Listening settings now offer one mode choice, optional Strong background-noise rejection, and adaptive pauses for unfinished phrases. Microphone mute preserves a spoken answer. A speech-like interruption pauses playback until words are recognized; empty recognition resumes it. Stop invalidates old queued input. Oversized requests are rejected with a retry notice. `tools/listening_flow_check.py` exercises these paths with virtual audio. Strong rejection can miss quiet speech; wake mode or hold-to-talk is recommended around TV and other people.

### Peek action feedback and companion surface (1.10.0)

The attached companion surface appears on hover and joins captions, current activity, microphone, Stop and conversation controls. More controls and recent action details expand in place. Peek stays at the same screen position when the surface expands where screen space permits. The companion looks toward a fresh desktop action target while working, turns toward you during speech or a question, and follows the cursor when idle. Targets expire after five seconds. On entry, Peek grips the screen edge before easing his head into view; on exit, he tucks his head away before releasing his hands. The 620 ms entrance and 420 ms retreat reverse from their current position when toggled quickly. Input stops immediately on exit, while the renderer stays alive until the retreat finishes. Reduced motion skips these transitions and stops the audio meter.

A finished reply displays **Reply ready**. **Actions verified** requires readback evidence for every recorded action, with no unfinished, failed, missing or untracked action results. Supported checks include config writes/restores, accessible text-field changes, window focus, and local volume/brightness/mute/workspace/play-pause controls. Application launch, browser navigation, clicks and arbitrary CLI tools remain **Review the result** unless their outcomes have a supported check. A screenshot or a tool's success text alone cannot establish verification. The success reaction is reserved for verified action results; this does not certify that every part of an arbitrary user goal was fulfilled.

Action details retain up to 200 steps for the current turn, publish the latest 12, and show the latest four when expanded. Full native tool output remains in the conversation. Switching conversations clears the companion's action status. This is current-turn feedback, not a persistent workflow scheduler or automatic task resumption.

Unused conversations now follow a changed Omarchy default on startup and the next three-second refresh. The header, composer and permission choices update together; drafts and working folders are preserved. Conversations with messages or an existing native/terminal session keep their original agent.

### Expressive face and voice readiness

Finishing local voice warmup triggers a brief ready nod, brighter eyes, lifted antenna and smile before settling into listening. Live speech immediately takes priority over that flourish. Listening leans closer and shows an audio meter driven by measured microphone levels; hearing speech adds attentive nods and larger eyes. Thinking squints and scans, working taps its fingers, speaking moves its mouth with playback, questions raise a brow, errors frown and shake, and verified success gets a larger smile and celebration. The eyes, face tint, trim and antenna use distinct theme-derived state colors. The Expression slider scales movement; reduced motion keeps static state expressions and colors. These previews are available under Companion → Appearance.
