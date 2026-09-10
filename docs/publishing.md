# Publishing Side Chat

Side Chat follows the Git install/update pattern in the local
`omarchy-agents` repository. Its plugin ID is `blr.side-chat`; it is a
service and does not replace Omarchy's Agents bar widget.

## Before publishing

The public repository is [baileyrosen3/side-chat](https://github.com/baileyrosen3/side-chat).
Keep one plugin and its `manifest.json` at the repository root. Include
`setup.py`, the full `peek/` source and `Cargo.lock`, `deploy/`, companion
assets, the README, `LICENSE`, `COPYING.PEEK`, and `THIRD_PARTY.md`.

Do not commit development import symlinks (`Commons`, `Ui`), Python caches,
runtime environments, credentials, chat history, downloaded models, or Rust
build output. Omarchy validation rejects symlinks anywhere in the checkout.
The ignore rules exclude the local import links; validate a **clean clone**,
not a working directory containing those links.

From the clean release clone:

```bash
omarchy plugin validate .
python3 -B -m unittest discover -s tests -v
python3 setup.py --check
```

The release tests require the runtime status to obtain its version from the
host-injected manifest and require Preferences to display it. Do not add a
second hard-coded QML version; bump `manifest.json` once per release instead.

Test the README's Git install on a fresh Omarchy Quattro user/session, then
enable, disable, update, and remove the plugin. Test chat without the speech
runtime first. Test the default Voxtype setup without an existing local model
or Hugging Face cache, then test the opt-in `--with-parakeet` and
`--with-legacy-asr` downloads as well as model reuse. Finish the manual
desktop/audio checks in [TEST_PLAN.md](../TEST_PLAN.md). Dependency diagnostics
do not establish microphone quality, provider authentication, or end-to-end
speech readiness.

Use `omarchy plugin update blr.side-chat --yes` for the documented trusted
Git update path. Omitting `--yes` intentionally prints the incoming diff and
asks for confirmation. Follow the update with `omarchy restart shell`; the
updater requests a hot rescan, but restarting the long-running Quickshell
process guarantees that cached nested QML types are replaced. The custom
`install.py` copies development builds into timestamped runtime directories;
it must not be used to replace a Git-managed installation. Omarchy never
executes setup hooks during add/update, so dependency installation remains
the documented `python3 setup.py` step.

For releases that change dependencies, call out the setup flags users must
rerun. The host injects `manifest.json` into `Main.qml`, making its version the
single source for IPC status and the Preferences label. A root `preview.png`
showing the real interface is optional; use fixture content without private
conversations.

## Marketplace listing

The marketplace requires a public GitHub repository, a valid manifest,
installation/removal instructions, and license/dependency documentation.
Submit through the [plugin submission form](https://github.com/omacom/omarchy-plugin-marketplace/issues/new?template=submit-plugin.yml)
after the public release is ready. See the
[publishing guide](https://plugins.omarchy.org/publish.html) and
[submission format](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SUBMISSION.md).

Suggested listing values:

| Field | Value |
| --- | --- |
| Title | `[Plugin]: Side Chat` |
| Repository | The public Side Chat GitHub repository root URL |
| Category | Developer Tools |
| Tags | ai, hyprland, quickshell |

Maintainer notes: Side Chat hosts native coding-agent sessions and optional
local voice/computer control. Python speech packages and model downloads
are installed explicitly into a private user runtime. Desktop input access
is opt-in through `--with-desktop-input`; the README lists its system files
and removal steps. No dependency installer runs on plugin enable.

The owner needs to review the submission form's ownership and other
statements before submission. Listing requires the marketplace's review
of the submitted commit; a prepared repository is not a published listing.
For subsequent releases, follow its
[verification/update process](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/VERIFICATION.md).
