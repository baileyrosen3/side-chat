# Shared workspace validation — 2026-09-11

## Version 1.15.2

- Keypad: web apps on **7–9**, sections on **4–6**, and tap-to-toggle listening on **1–3**. **0** toggles Peek; **.** toggles Peek's microphone. Bare **Numpad Enter** restores system dictation, with the Super chord retained as an alias.
- Thoughts QML: **24 passed**, including second tap before recorder startup, note/task transcript destinations, preserving previous drafts, and ignoring repeated taps during transcription. Existing Python storage/voice tests: **21 passed**. JavaScript routing and draft/filter checks passed.
- Native Main/ChatWindow fixture verified section navigation, both note/task voice toggles, Chat remaining open while toggling Peek listening, preserved drafts, and decimal routing. Voice commands were intercepted; no microphone or agent was activated. Fixture data and keyboard focus were isolated from the desktop.
- Peek controller's fast double-tap checked with a mocked speech worker: start followed by finish, even before the microphone acknowledges starting.
- Lua mapping checked for explicit unbinding, duplicate chords, requested web apps, 0/decimal, both system-dictation press/release pairs, and unchanged media controls. All **121** packaged files exist and packaged Python syntax passes.
- [Current keypad map and temporary shortcut locations](keypad.md).

## Version 1.15.1

- Keypad routing checks passed: destinations, capture, companion controls, and stopping; no global shortcut sends a message.
- Thoughts QML: **21 passed**, including new-note/voice-note capture from To-dos with the previous draft retained. Workspace QML: **8 passed**.
- Existing storage and voice tests: **21 passed**, including release before recording startup, cancellation, and microphone ownership.
- Native fixture verified Chat/Notes/To-dos keys, fresh note from a task draft, search toggling, history focus, populated preferences, and workspace show/hide. The fixture used isolated data and disabled compositor keyboard focus.
- Lua mapping checked for duplicate chords, explicit unbinding, preserved 0/. behavior, press/release pairs, temporary WinBoat/Browser assignments, and unchanged media keys.
- [Keypad map and temporary shortcut locations](keypad.md).

## Version 1.15.0

- Full Python suite: **236 tests, 219 passed, 17 skipped** for optional speech dependencies.
- Thoughts QML: **19 passed**; workspace QML: **8 passed**, with warnings treated as failures.
- New checks cover date previews, DST gaps, stale parse results, reminder delivery and retries, stale notification actions, full-content search, capture without modifying the clipboard, source metadata, deleted-item recovery, and consistent private exports without overwriting files.
- A private D-Bus notification service exercised the real notification helper: delivery acknowledgment, escaped text, all three action buttons, and routing an action back to the app. No desktop notification or real task was used.
- Native Main/ChatWindow fixture: reminder preview → saved task with the displayed timestamp; unified search across all three item kinds; capture draft; Recently deleted → restore; `.zip` export. Keyboard focus reached the task editor on opening and the search/capture inputs in those views.
- Fixed a first-open keyboard-focus race by retrying once after the compositor commits the drawer surface.
- README screenshots use isolated fixture content. Final screenshot capture disables compositor keyboard focus so it cannot intercept typing in another app.
- Runtime files are checked for syntax and completeness; plugin validation runs on the install staging tree. The source checkout contains development symlinks rejected by the distributable-plugin validator, and an unchanged, uninstalled `tools/wake_live_check.py` helper has a pre-existing syntax error.
- Super+F2 was unused before adding selected-text capture. F1 and Super+F1 retain their existing bindings.

Additional focused checks:

```sh
python3 -B -m unittest discover -s tests -p test_workspace.py -v
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  /usr/lib/qt6/bin/qmltestrunner -input tests/qml/tst_workspace.qml \
  -import tests/qml/imports -v1
```

## Version 1.14.1


Version 1.14.1 integrates Chat, Notes, To-dos, and Peek in the existing edge
drawer. Notes has no independent PanelWindow. The common app header and tab
navigation remain visible across sections; Peek controls share that navigation.

Validation:

- Python: **219 tests, 202 passed, 17 skipped**. Skips require optional speech
  dependencies unavailable to system Python. Storage tests cover original
  Markdown, conflicts, drafts, reversible deletion, and microphone ownership.
  Local voice integration covers saving notes/to-dos and navigating/searching
  the correct tab without sending an agent request.
- Thoughts UI: **15 passed**, both offscreen and on the desktop renderer.
  Covers shared navigation, independent chat/note drafts, focus and shortcut
  isolation, save acknowledgment, voice navigation, cancellation on leaving
  capture, completion animations, recovery, and narrow layouts.
- Companion task surface: **13 passed** on the desktop renderer, including
  navigation into Notes/To-dos and existing robot feedback during recording,
  transcription, and saving.
- Full desktop QML run: **90 passed, 3 failed** before the final three focused
  cases were added. The unchanged baseline had **76 passed and the identical
  three PanelOutline failures**. The final additions passed in targeted runs.
- JavaScript filtering/recovery checks passed.
- An isolated native Quickshell fixture exercised the actual Main/ChatWindow
  integration: open Notes, enter a draft, switch to Chat, restore the same
  draft, save Markdown, switch to To-dos, and close the drawer. Input focus
  followed the active section. No standalone Thoughts surface was created.
- A second native check kept the drawer open with Peek and navigated to To-dos
  through the companion's shared tabs. The screenshots use isolated fixture
  content; no microphone, agent request, or real notes were used.

Run focused checks:

```sh
python3 -B -m unittest discover -s tests -p 'test_thoughts.py' -v
node tests/thoughts-model.test.cjs
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  /usr/lib/qt6/bin/qmltestrunner -input tests/qml/tst_thoughts.qml \
  -import tests/qml/imports -v1
```

F1 capture and Super+F1 retain their IPC commands and now open the shared drawer.
The install keeps a backup of the previous Git checkout and configuration;
existing Markdown files are checked for changes after installation.
