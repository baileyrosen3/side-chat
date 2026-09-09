# Peek companion upgrade

Authorized: implement all eight proposed additions, preserving the Omarchy default CLI, theme, free/open-source dependencies, and existing chat/terminal session.

- Wake word: local Hey Jarvis detector, hidden-panel standby, bounded follow-up window, explicit off control.
- Screen context: optional active-window metadata, selected text, on-demand screenshot; highlight observed targets.
- Memory: explicit remember/forget commands, local persistent records and editable UI.
- Fast commands: bounded native command router for volume, brightness, media, app/browser launch and workspaces.
- Steering: pause computer input at speech onset, deliver corrections to the same native session, retain the interrupted task.
- Routines/monitoring: editable named sequences of allowed commands, timers and explicit process-completion watches, local notifications.
- App control/undo: AT-SPI semantic inspection and actions with stale-target checks; transactional configuration writes and conflict-aware restore.
- Companion: context-directed gaze, real activity caption, completion response and configurable speaking personality.

Implemented all eight features in 1.4.0. Verification: 60 automated tests; synthetic virtual audio wake/follow-up/Parakeet/local-command/TTS round trip; real OMP tracked config editing and mid-tool steering; real GTK semantic editing/clicking with stale-target rejection and config restore; offscreen themed QML rendering. The desktop was locked during final testing, so compositor focus and a visible production screenshot remain unverified for this update. The GTK fixture supplied its own focus metadata during that check.

Installation now uses fresh, build-specific QML component paths and verifies both UI version and loaded path. This avoids cached nested QML without restarting the shared shell or disturbing its lock service. Existing Javert voice, Parakeet model, agent settings, and history were preserved. Wake listening is available but off until selected in Listening settings.
