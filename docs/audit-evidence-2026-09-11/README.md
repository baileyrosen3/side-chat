Evidence for [the Side Chat audit](../audit-2026-09-11.md).

All captured content is synthetic. The native fixture used a temporary source copy and disabled the drawer's compositor keyboard focus/grab. No microphone or provider turn was started. Its added workspace contracts were fixture adaptations, not application fixes.

The diagnostic probes deliberately assert the defective behavior observed during the audit. A passing probe confirms reproduction; these are not acceptance tests asserting correct behavior. After fixes, the expectations should be reversed before adding equivalent cases to the normal test suite.

Run the local probes from the repository root:

```sh
python3 -B docs/audit-evidence-2026-09-11/reproduce.py
node docs/audit-evidence-2026-09-11/reproduce-transitions.cjs
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=generic \
QT_QUICK_CONTROLS_STYLE=Basic QT_QUICK_BACKEND=software \
qmltestrunner -input docs/audit-evidence-2026-09-11/tst_audit.qml \
  -import tests/qml/imports -v1
```

The Python probe creates temporary Markdown and SQLite data, uses a mock native RPC session, and times local search. The JavaScript probe extracts the production transition functions into a request-recording context; it is not a compositor-level input test.

`preview-baseline.log` records the missing contracts in DesignPreview. `preview-current.log` contains the load measurement from the temporary adapted fixture; its remaining preferencesRequested warning belongs to that fixture. The screenshots show current components with fixture data. Geometry uses logical pixels; the captures reflect the display's device pixel ratio.

`source-fingerprints.json` records the working-tree hashes at completion. Its ChatWindow snapshot comparison is false because the temporary fixture disabled desktop focus capture. Other listed source files match the frozen copy.

The 236-check Python log has 17 system-runtime skips. The speech-runtime and Voxtype-runtime logs establish that all 17 passed with the installed optional dependencies. The eleven normal QML suite logs total 113 passes including initialization and cleanup. `qml-audit.log` is additional diagnostic evidence and is not included in that total.
