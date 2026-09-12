# Side Chat keypad

The bare numpad groups web apps, workspace tabs, and listening into three rows.
The middle and bottom rows follow the drawer's **Chat / Notes / To-dos** order.
Physical keycodes keep the layout the same with Num Lock on or off.

| 7 · ChatGPT | 8 · Gemini | 9 · Higgsfield AI |
| --- | --- | --- |
| **4 · Chat** | **5 · Notes** | **6 · To-dos** |
| **1 · Chat + listen** | **2 · Notes + listen** | **3 · To-dos + listen** |
| **0 · Toggle Peek** | **. · Toggle Peek microphone** | **Enter · Hold for system dictation** |

- **7 / 8 / 9** launch or focus ChatGPT, Gemini, and Higgsfield AI.
- **4 / 5 / 6** open Chat, Notes, and To-dos without starting their microphones.
- **1** opens Chat and starts Peek listening. Tap again to finish the voice
  request; Peek transcribes it and responds as usual.
- **2 / 3** open a fresh note or to-do and start recording. Tap again to stop
  and transcribe into a draft. Review, then save with the regular keyboard's
  **Ctrl+Return**. Previous unfinished writing stays in drafts. Regular
  **Return** still adds a to-do. Taps during transcription do not restart recording.
- **0** toggles Peek itself; **.** toggles its microphone on and off. The decimal
  key uses the same microphone as **1** without opening the Chat drawer.
  Finish a recording before switching voice destinations. Pressing another
  voice key during note/task capture finishes the current capture first.
- **Enter** records system dictation while held; release to type into the
  focused application. **Super+Enter** also works as an alias.
- **Ctrl+K** searches inside the app. History and Preferences are in the header.
  Selected-text capture remains available through `captureSelection` IPC;
  copied text can be captured with the Clipboard button in search.
- **Clear / Num Lock** hides the drawer; **/** stops a reply or recording;
  **=** opens Peek's controls. **+ / −** keep volume control, and **\*** keeps play/pause.
- **F1, Super+F1, and Super+F2** no longer trigger Side Chat. Their app actions
  have moved to the keypad. F1 is available to the focused application again.

## Temporary homes for previous actions

These are temporary until their permanent positions are chosen. **Super** means
the modifier plus the physical **numpad** key, not the number row.

| Temporary shortcut | Previous action |
| --- | --- |
| Super + 7 | Claude |
| Super + 8 | ChatGPT |
| Super + 9 | Higgsfield AI |
| Super + 4 | X |
| Super + 5 | GitHub |
| Super + 6 | Gmail |
| Super + 1 | Riptide |
| Super + 2 | WinBoat |
| Super + 3 | Browser |
| Super + Enter, held | System dictation alias (also on bare Enter) |
| Super + Clear / Num Lock | Close the focused window |
| Super + = | Send the focused window to the stash |

The active Browser and WinBoat assignments are preserved, including overrides
from the keybinding editor. Other existing shortcuts for those apps still work.

## Configuration

The installed mapping lives in `~/.config/hypr/side_chat_keypad.lua`, loaded last
by `require("hypr.side_chat_keypad")` in `bindings.lua`. The reviewable source is
[`deploy/side-chat-keypad.lua`](../deploy/side-chat-keypad.lua).
The keycodes in that file match this machine's Magic Keyboard. Check your own
layout and existing shortcuts before copying it to another machine.

After editing the mapping, run `hyprctl reload` and `hyprctl configerrors`.
