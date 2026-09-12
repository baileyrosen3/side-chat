Side Chat — UI and interaction hardening

Implemented September 12, 2026, following the [full product audit](audit-2026-09-11.md). The initial validation below used the development workspace without replacing the desktop plugin. No real provider request, microphone recording, or physical desktop action was started by these checks. A subsequent device update exposed the additional startup issue recorded below.

The visual direction preserves Peek, the screen-edge silhouette, and live Omarchy colors and fonts. The surrounding workspace now uses consistent rounded controls, fewer competing status indicators, visible Save/Add/Send labels, and a separate Stop action. Notes grows with its content. Secondary message actions remain discoverable, code retains indentation with horizontal scrolling, and settings return to the page that opened them.

Screenshots use synthetic content. Sample conversation text is not a test result. See [Notes](audit-fixes-evidence-2026-09-12/notes.png), [Stop while using Notes](audit-fixes-evidence-2026-09-12/notes-working.png), [Stop and Redirect](audit-fixes-evidence-2026-09-12/redirect.png), [long attachment](audit-fixes-evidence-2026-09-12/attachment.png), [search match](audit-fixes-evidence-2026-09-12/search-match.png), and [code](audit-fixes-evidence-2026-09-12/code.png).

**Changes against the original findings**

| Audit | Implemented behavior |
| --- | --- |
| 1 · Startup cancellation | Native startup checks cancellation before delivering a prompt. Adapter handshake waits are interruptible. A stopped startup produces a stopped reply without sending the queued task. |
| 2 · Draft transitions | New/Open flush outgoing drafts. Text, source, attachment references, and a separate in-progress edit are persisted. Cancel restores the original draft. Repeated Edit actions preserve unfinished edits. Drafts also save during a running reply. Redirect text clears only after acknowledgment. |
| 3 · Unexpected screen context | Generic words such as “this” and “error” no longer trigger capture. Explicit screen language uses a shared pattern exposed to the UI. A visible context chip can exclude the active window from a typed submission. Existing Always/Off preferences remain available. |
| 4 · Conversation rendering | A virtualized ListView creates only nearby messages. Persisted message identities and incremental model updates retain unchanged delegates and text selection. Closed drawers release their message delegates. Tool details and completed task rows load when expanded. |
| 5 · Physical takeover | Takeover stays armed between desktop operations until control stops or the turn changes. Capability reporting uses readable input devices; the emergency shortcut is advertised only when an appropriate keyboard is monitored. Settings expose the actual capability. |
| 6 · Damaged recovery data | Corrupt chat/settings JSON is preserved in a recovery table before removal from active records. Invalid draft JSON is preserved in a separate recovery file. Note saves use stable draft identities and operation tokens so retries cannot duplicate a committed note. Cleanup failure reports that the note was saved. |
| 7 · Reminder races | Noon and midnight require a current reminder preview before Save. Stale preview responses remain ignored. |
| 8 · Attachment overflow | Attachment width is bounded by the actual Flow width; labels elide while removal remains visible. |
| 9 · Stopped results | Collapsed tool activity separately counts completed, failed, and stopped operations. Completion is not labeled verification. |
| 10 · Preview drift | DesignPreview owns real Thoughts/Workspace models and the current navigation contract. It includes long-history, attachment, redirect, code, and text-selection probes. It does not capture desktop keyboard focus. |
| 11 · Erased drafts | Clearing a new draft sends a deletion to recovery storage. Local tombstones prevent stale snapshots from resurrecting it; reconnect retries pending clears. |
| 12 · Result navigation | Local file links open the configured Omarchy editor, including supported line arguments. Search results carry their matching message index and open it with a visible highlight. |
| 13 · Settings routes | A page stack restores Notes, To-dos, History, or Preferences through nested settings. Application preferences remain accessible while an agent runs; session mutations retain their busy guards. Copy explicitly describes immediate versus Save behavior and the scope of agent defaults. |
| 14 · Readability and access | Core controls have larger targets and consistent visible focus. Notes and task bodies follow the theme font size. Primary actions have text labels. A 280-pixel Notes fixture also passes with a 22-pixel body font. |
| 15 · Search and exports | A maintained SQLite FTS5 trigram index narrows substring searches. SQL ranks before transferring message bodies to Python. Search returns at most 40 conversation candidates before combining with Notes. Exports use a separate worker. |
| 16 · Motion and monitors | Nonessential control fades are removed or honor reduced motion. An open drawer relocates to an available screen when its monitor disappears. |

**Validation**

The full system-Python suite collected 249 tests: 232 passed and 17 required the installed voice runtime. Those 17 passed there (12 speech-interruption checks and five worker checks within the 16-test Voxtype suite). All 249 distinct Python checks passed across the appropriate runtimes. Three JavaScript test scripts passed, including extracted production navigation/draft functions. Twelve QML suites passed 120 checks, including initialization and cleanup. Focused recovery checks were repeated after the final cleanup-error wording change.

Native QML tests ran on Wayland/OpenGL, including Peek’s 3D surfaces. The 2D suites used Qt’s offscreen software renderer. The native preview loaded, exercised the completed layouts, and exited cleanly. Main.qml also parsed successfully, the 121-file development install manifest passed its check against a temporary destination, and `git diff --check` passed.

Reproduce UI checks with `bash tools/validate-ui.sh`. Use `python3 -B tools/benchmark_workspace.py` for the synthetic mature-library search measurement. UI tests require the local Omarchy/Qt environment; the native suites need a Wayland session. SQLite must provide FTS5 and the trigram tokenizer, as the tested Arch build does. The search index is derived data; conversation JSON remains the source of truth and is included in backups.

| Controlled measurement | Audit fixture | Final implementation fixture |
| --- | --- | --- |
| 1,000 messages, assignment to next Qt callback | 2,380 ms | 31 ms, including the stable message model |
| Live delegates at the latest message | All 1,000 | 3 |
| Selected earlier text after updating a reply | Not established | Same delegate; selected text preserved |
| Long attachment in a 337-pixel drawer | 803 pixels wide | 202 pixels wide; right edge at 215 |
| Search: 2,000 notes and 1,000 chats, warm samples | About 185–189 ms | 75.8, 84.2, 81.7 ms |

These are local fixture samples, not percentile targets or guarantees for every machine. The final search fixture’s cold sample was 136.6 ms. [Logs and measurements](audit-fixes-evidence-2026-09-12/) record the checks. The 21st catalog returned HTTP 401, so this implementation reused native project primitives. Its review command inspected zero QML files; native tests and rendered inspection provide the UI evidence.

**Remaining release checks and product work**

One Quickshell process crashed during repeated development reloads. Its core identifies SIGSEGV in the Qt Quick rendering path, with mostly unresolved frames and only the crash-handler thread available. No out-of-memory event was found. This is evidence of a rendering failure during reload, not proof of its root cause. Subsequent fresh previews and native suites passed. No production data was involved. During the subsequent device update, the Git fast-forward completed but the hot rescan stopped answering IPC. Omarchy's guarded shell restart restored the shell. The documented restart step remains necessary; no claim is made that the underlying reload failure is fixed.

Real provider initialization/branch cancellation, physical mouse takeover between actions, device removal, microphone interruption, monitor removal, and screen-reader operation still need live acceptance checks. Automated fixtures establish the code behavior without claiming those hardware integrations were exercised.

The next product iteration should concentrate on first-run agent/voice readiness, a richer preview of exactly which app and image will be shared, and usability sessions with people who have not seen the project. The implemented corrections improve the existing interface; award-level quality still needs that external evidence and refinement.

**Device update follow-up · 1.16.1**

The installed library exposed a missing combination in the original tests: reminder polling with an existing draft recovery file. The reminder checker already held the Thoughts file lock, then its snapshot tried to acquire the same lock through a second file descriptor. The backend blocked and Notes could not load, while its files remained intact. Version 1.16.1 passes the existing lock state into the snapshot's draft read.

The new regression uses a child process with a five-second deadline and real file locking. It reproduces the hang against 1.16.0, then passes with the fix, verifies reminder deduplication, preserves a valid draft, and recovers malformed draft data without blocking. All 18 workspace checks passed. A full system-Python rerun collected 250 checks: 233 passed and the same 17 optional voice-runtime checks were skipped; their prior runtime results remain above. See [the follow-up Python log](audit-fixes-evidence-2026-09-12/deployment-python.log). UI code is unchanged from the 120-check QML validation.
