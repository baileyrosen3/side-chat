# Shared Voxtype compatibility

Side Chat updates only the plugin. They do not install the maintainer's local
Voxtype build, replace your daemon, or change your keybindings.

Unpatched Voxtype 1.0.1 ignores private file output in its streaming path.
That can type a Peek request into the focused application instead. Peek
conservatively blocks a running daemon that identifies itself as exactly
`1.0.1`, even if streaming is currently disabled. The check reads the daemon's
runtime version, not the separately installed CLI version. It is a known-version
guard, not a general capability test for every older or future build.

The tested upstream revision containing the fix is
[`320a737e5d3c8662e0ec7de95f75407baa784d82`](https://github.com/peteonrails/voxtype/commit/320a737e5d3c8662e0ec7de95f75407baa784d82).
This is a development revision, not a Side Chat binary release. If you prefer
not to build development software, install `python3 setup.py --with-parakeet`
and select **Parakeet Unified** in Peek settings. That alternative uses a
separate recognizer and more memory if regular Voxtype stays loaded.

## Build the pinned daemon (advanced, Linux CPU)

Use a new source directory. Install Rust/Cargo and the build dependencies
documented in that revision's upstream README first. Compilation and upstream
dependency downloads can take several minutes and substantial disk space.

```bash
git clone https://github.com/peteonrails/voxtype.git voxtype-peek-build
cd voxtype-peek-build
git checkout --detach 320a737e5d3c8662e0ec7de95f75407baa784d82
```

In `Cargo.toml`, change only the package's version from `1.0.1` to
`1.0.1-peek-streaming-fix`. This labels the patched daemon so the compatibility
guard can distinguish it from the affected release. Then build:

```bash
cargo build --release --bin voxtype --features 'parakeet,moonshine,sensevoice,paraformer,dolphin,omnilingual,cohere,ml-diarization'
install -Dm755 target/release/voxtype "$HOME/.local/share/voxtype/bin/voxtype-peek-streaming"
```

This CPU build does not include CUDA, Metal, or OpenVINO engines. Do not use it
to replace a daemon configured for one of those engines without adapting the
upstream build. It does not download or change your recognition model.

With both Peek and regular dictation idle, open the user service editor:

```bash
systemctl --user edit --drop-in=peek-streaming.conf voxtype.service
```

Add this override. If a file with that name already exists, preserve a backup
before changing it:

```ini
[Service]
ExecStart=
ExecStart=%h/.local/share/voxtype/bin/voxtype-peek-streaming daemon
```

Then apply and check:

```bash
systemctl --user daemon-reload
systemctl --user restart voxtype.service
systemctl --user status voxtype.service
voxtype status --format json
```

The packaged `/usr/bin/voxtype` remains unchanged and can still control the
shared daemon. In the plugin checkout, run
`python3 setup.py --check --with-voxtype`. This catches the known affected
daemon; a successful dependency check is not an end-to-end microphone test.

## Use and verify

With the README's example bindings: tap Decimal, speak a short request, then
tap Decimal again. The words should reach Peek, not the focused application;
the reply should appear in chat and play on the configured output. Input
levels come from Voxtype's existing telemetry socket, not another recorder.
Then, separately, verify your existing Enter dictation binding still works.
Do not run the two recording modes simultaneously.

Custom Voxtype overlays must honor `$XDG_RUNTIME_DIR/voxtype/osd_suppressed`
to hide during Peek recordings. Side Chat does not rewrite third-party OSD
files. An overlay appearing is not, by itself, proof of transcript misrouting.

## Roll back

With recording idle, move only `peek-streaming.conf` out of
`~/.config/systemd/user/voxtype.service.d/` and keep it as a backup. Reload
systemd and restart `voxtype.service` with the commands above. This restores
the packaged service command without removing other user overrides. Keep Peek
on its optional local recognizer if the packaged daemon is still affected.

Once you install an upstream release confirmed to contain the fix, remove
this override the same way and repeat the private-transcript check.
