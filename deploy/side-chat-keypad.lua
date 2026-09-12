-- Side Chat / Peek keypad, for the current Magic Keyboard layout.
-- Load LAST from ~/.config/hypr/bindings.lua. Physical codes ignore Num Lock.
-- Top row = web apps; middle = sections; bottom = listening in those sections.
-- Super + keypad preserves earlier displaced shortcuts temporarily.

-- Remove previous physical bindings and the symbol aliases used for Peek.
for _, code in ipairs({77, 79, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 104, 106, 125}) do
  hl.unbind("code:" .. code)
end
for _, code in ipairs({77, 79, 80, 81, 83, 84, 85, 87, 88, 89, 104, 125}) do
  hl.unbind("SUPER + code:" .. code)
end
for _, symbol in ipairs({"KP_0", "KP_Insert", "KP_Decimal", "KP_Delete"}) do
  hl.unbind(symbol)
end

-- Previous Side Chat shortcuts now live on the keypad.
hl.unbind("F1")
hl.unbind("SUPER + F1")
hl.unbind("SUPER + F2")

-- Top row: preferred web apps.
o.bind("code:79", "ChatGPT", { webapp = "https://chatgpt.com", focus = true })
o.bind("code:80", "Gemini", { webapp = "https://gemini.google.com", focus = true })
o.bind("code:81", "Higgsfield AI", [[omarchy-launch-or-focus-webapp "Higgsfield AI" "https://higgsfield.ai/"]])

-- Middle row: open a section without starting its microphone.
o.bind("code:83", "Side Chat: Chat", "omarchy-shell blr.side-chat keypad chat")
o.bind("code:84", "Side Chat: Notes", "omarchy-shell blr.side-chat keypad notes")
o.bind("code:85", "Side Chat: To-dos", "omarchy-shell blr.side-chat keypad todos")

-- Bottom row: open and listen; press the same key again to stop listening.
o.bind("code:87", "Side Chat: Chat and toggle listening", "omarchy-shell blr.side-chat keypad listen-chat")
o.bind("code:88", "Side Chat: Notes and toggle recording", "omarchy-shell blr.side-chat keypad listen-notes")
o.bind("code:89", "Side Chat: To-dos and toggle recording", "omarchy-shell blr.side-chat keypad listen-todos")

-- Preserve the familiar companion controls.
o.bind("code:90", "Toggle Peek", "omarchy-shell blr.side-chat keypad peek")
o.bind("code:91", "Toggle Peek microphone", "omarchy-shell blr.side-chat keypad microphone")
o.bind("code:104", "System dictation: hold", "voxtype record start", { locked = true })
o.bind("code:104", "System dictation: release", "voxtype record stop", { release = true })
o.bind("code:106", "Side Chat: Stop reply or recording", "omarchy-shell blr.side-chat keypad stop")
o.bind("code:77", "Side Chat: Hide workspace", "omarchy-shell blr.side-chat keypad hide")
o.bind("code:125", "Side Chat: Peek controls", "omarchy-shell blr.side-chat keypad controls")

-- Temporary homes for the displaced actions. These were unused chords.
o.bind("SUPER + code:79", "Claude (temporary)", { webapp = "https://claude.ai", focus = true })
o.bind("SUPER + code:80", "ChatGPT (temporary)", { webapp = "https://chatgpt.com", focus = true })
o.bind("SUPER + code:81", "Higgsfield AI (temporary)", [[omarchy-launch-or-focus-webapp "Higgsfield AI" "https://higgsfield.ai/"]])
o.bind("SUPER + code:83", "X (temporary)", [[omarchy-launch-or-focus-webapp "X" "https://x.com/"]])
o.bind("SUPER + code:84", "GitHub (temporary)", [[omarchy-launch-or-focus-webapp "GitHub" "https://github.com/"]])
o.bind("SUPER + code:85", "Gmail (temporary)", [[omarchy-launch-webapp "https://mail.google.com"]])
o.bind("SUPER + code:87", "Riptide (temporary)", [[omarchy-launch-or-focus ^tradewasm$ "uwsm-app -- /home/blr/.local/bin/riptide"]])
o.bind("SUPER + code:88", "WinBoat Windows Desktop (temporary)", "uwsm-app -- /home/blr/.local/bin/winboat-desktop")
o.bind("SUPER + code:89", "Browser (temporary)", "omarchy-launch-browser")
o.bind("SUPER + code:104", "System dictation: hold (temporary)", "voxtype record start", { locked = true })
o.bind("SUPER + code:104", "System dictation: release (temporary)", "voxtype record stop", { release = true })
o.bind("SUPER + code:77", "Close window (temporary)", hl.dsp.window.close())
o.bind("SUPER + code:125", "Send window to stash (temporary)", hl.dsp.window.move({ workspace = "special:scratchpad", follow = false }))

-- + / - retain volume control; * retains media play/pause from bindings.lua.
