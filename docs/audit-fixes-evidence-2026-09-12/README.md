Evidence from the September 12 UI and interaction implementation.

The screenshots contain synthetic conversation content. The automated test logs, not sample assistant prose in screenshots, establish the validation results. Some screenshots were captured during the implementation; `handoff-*.png` captures use the completed visual components.

- `python.log`: complete system-Python run; 249 collected, 232 passed, 17 require the voice runtime.
- `speech.log` and `voxtype.log`: installed voice-runtime checks, including all 17 initially skipped tests.
- `qml.log`: 120 checks across eight 2D and four native Wayland/OpenGL suites.
- `javascript.log`: all three JavaScript scripts, including the production Main.qml transition functions.
- `final-recovery.log` and `final-thoughts.log`: focused validation after the final partial-save error handling change.
- `deployment-python.log`: 250 checks after fixing the reminder/draft lock conflict discovered during device update; 233 passed and 17 optional-runtime skips.
- `measurements.json`: controlled geometry, message rendering, and search observations.

Native preview observations: the final 1,000-message assignment reported `THOUSAND_MESSAGES_MS 31`; its 337-pixel panel had three live message delegates. The selection probe reported `SELECTION_CHECK {"sameDelegate":true,"selectedText":"Select"}` after updating another reply. Fresh previews reached `Configuration Loaded` and exited with code 0 without QML warnings.

A separate development-reload crash occurred in Quickshell PID 3559504 at September 12, 01:40:03 EDT. `coredumpctl info` reported SIGSEGV in `QSGRenderThread`. The available GDB stack contained the Quickshell signal handler and unresolved Qt Quick/Core frames; it exposed only one thread. Memory was not exhausted and the queried kernel journal contained no OOM event. This does not establish a specific root cause. No extracted core file was retained in this repository. The implementation record keeps the reload path as a release check.
