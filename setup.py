#!/usr/bin/env python3
"""Prepare Side Chat dependencies without replacing the Omarchy plugin checkout."""
import argparse
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

SOURCE = Path(__file__).resolve().parent
PLUGIN = "blr.side-chat"
BASE_PACKAGES = ("python", "python-gobject", "qt6-quick3d", "wl-clipboard")
PEEK_PACKAGES = (
    "base-devel", "pipewire", "pipewire-audio", "pipewire-pulse", "wireplumber",
    "libpulse", "libsndfile", "chromium", "grim", "wtype",
    "at-spi2-core", "brightnessctl", "playerctl",
)
VOXTYPE_PACKAGES = ("voxtype-bin",)
INPUT_FILES = {
    "deploy/70-side-chat-input.rules": "/etc/udev/rules.d/70-side-chat-input.rules",
    "deploy/side-chat-input.conf": "/etc/modules-load.d/side-chat-input.conf",
}


def run(command, **kwargs):
    print("+ " + shlex.join(map(str, command)), flush=True)
    return subprocess.run(command, check=True, **kwargs)


def missing_packages(with_peek=False, with_voxtype=False, with_parakeet=None):
    # Preserve the old helper behavior for callers that do not specify an
    # engine; the top-level setup path passes an explicit False for its new
    # Voxtype-first default.
    if with_parakeet is None:
        with_parakeet = with_peek and not with_voxtype
    packages = list(BASE_PACKAGES)
    if with_peek:
        packages.extend(PEEK_PACKAGES)
        # Respect existing mise/rustup installations rather than introducing a
        # conflicting Rust package or a second uv installation.
        if not shutil.which("uv"):
            packages.append("uv")
        if with_parakeet and not (shutil.which("cargo") and shutil.which("rustc")):
            packages.append("rust")
    if with_voxtype:
        packages.extend(VOXTYPE_PACKAGES)
    return [package for package in packages if subprocess.run(
        ["pacman", "-Q", package], stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, check=False).returncode != 0]


def agent_problem(with_peek=False):
    from backend import AGENTS
    from agent_session import NATIVE_AGENTS

    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    try:
        agent = (config / "omarchy/defaults/agent").read_text().strip()
    except OSError:
        agent = ""
    agent = {"oh-my-pi": "omp", "claude-code": "claude", "open-code": "opencode",
             "gemini-cli": "gemini", "github-copilot": "copilot"}.get(agent, agent)
    if agent not in AGENTS or not shutil.which(agent):
        return ("Choose and install an agent with `omarchy default agent <name>` "
                "(omp, pi, codex, or claude), then complete its sign-in in the terminal.")
    if with_peek and agent not in NATIVE_AGENTS:
        return "Peek requires omp, pi, codex, or claude as the Omarchy default agent."
    print(f"Agent: {agent} is on PATH. Account sign-in must be checked in its terminal.")
    return None


def input_problems():
    problems = []
    if not os.access("/dev/uinput", os.R_OK | os.W_OK):
        problems.append("/dev/uinput is not readable/writable by this user.")
    readable = {"keyboard": False, "pointer": False}
    for device in Path("/dev/input").glob("event*"):
        info = subprocess.run(["udevadm", "info", "--query=property", "--name", str(device)],
                              capture_output=True, text=True, check=False)
        properties = set(info.stdout.splitlines())
        if os.access(device, os.R_OK):
            if "ID_INPUT_KEYBOARD=1" in properties:
                readable["keyboard"] = True
            if {"ID_INPUT_MOUSE=1", "ID_INPUT_TOUCHPAD=1"} & properties:
                readable["pointer"] = True
    for kind, available in readable.items():
        if not available:
            problems.append(f"No readable {kind} device for physical takeover / Ctrl+Alt+Esc.")
    return problems


def require_peek_idle():
    """Refuse a voice-runtime replacement while the current worker is active."""
    status = subprocess.run(["omarchy-shell", PLUGIN, "status"], capture_output=True,
                            text=True, timeout=5, check=False)
    if status.returncode:
        return
    try:
        state = json.loads(status.stdout)
    except ValueError:
        raise SystemExit("Could not read Side Chat status. Disable the plugin before voice setup.")
    # `jarvis` is the state key used by installations before the Peek rename.
    voice = state.get("peek") or state.get("jarvis") or {}
    if state.get("busy") or (isinstance(voice, dict) and voice.get("enabled")):
        raise SystemExit("Finish the current reply and power Peek off before voice setup.")


def install_input_access():
    print("Granting the active local seat user access to keyboard/mouse events and uinput.\n"
          "This lets applications running as that user observe input and inject events.", flush=True)
    elevate = ["sudo"] if sys.stdin.isatty() else ["pkexec"]
    for relative, destination in INPUT_FILES.items():
        source, target = SOURCE / relative, Path(destination)
        if target.is_file() and target.read_bytes() == source.read_bytes():
            continue
        if target.exists() or target.is_symlink():
            raise SystemExit(f"Refusing to overwrite a different input policy: {target}")
        run(elevate + ["install", "-D", "-m", "0644", str(source), str(target)])
    run(elevate + ["modprobe", "uinput"])
    run(elevate + ["udevadm", "control", "--reload-rules"])
    run(elevate + ["udevadm", "trigger", "--subsystem-match=input", "--subsystem-match=misc"])
    run(["udevadm", "settle"])


def runtime_problems(with_kokoro=False, with_legacy=False, with_voxtype=False, with_parakeet=None):
    if with_parakeet is None:
        with_parakeet = not with_voxtype
    from peek.settings import DATA, DEFAULTS, model_path

    parakeet = DATA / "bin/peek-parakeet"
    if not parakeet.is_file() and (DATA / "bin/jarvis-parakeet").is_file():
        # Keep installations from before the Peek rename usable. The next
        # full setup run builds the new filename; the adapter can reuse this
        # binary in the meantime.
        parakeet = DATA / "bin/jarvis-parakeet"
    required = [DATA / "runtime/bin/python", DATA / "bin/agent-browser"]
    if with_parakeet:
        required.append(parakeet)
        required.append(DATA / "models/silero_vad.onnx")
        required.extend(model_path(DEFAULTS) / name for name in
                         ("encoder.onnx", "encoder.onnx.data", "decoder_joint.onnx", "tokenizer.model"))
    if with_legacy:
        required.append(DATA / "models/silero_vad.onnx")
    if with_kokoro:
        required.append(DATA / "models/kokoro-int8-multi-lang-v1_0/model.int8.onnx")
    if with_legacy:
        required.extend(DATA / "models/asr" / name for name in (
            "tokens.txt", *(f"{part}-epoch-99-avg-1-chunk-16-left-128.int8.onnx"
                            for part in ("encoder", "decoder", "joiner"))))
        required.append(DATA / "models/whisper-base.en/model.bin")
    problems = [f"Missing runtime file: {path}" for path in required if not path.is_file()]
    if with_voxtype and not shutil.which("voxtype"):
        problems.append("Voxtype executable is not on PATH. Install voxtype-bin and enable its user daemon.")
    elif with_voxtype and not with_parakeet:
        from peek.voxtype import compatibility_problem
        if problem := compatibility_problem():
            problems.append(problem)
    python = DATA / "runtime/bin/python"
    if python.is_file():
        imports = "import sherpa_onnx, numpy, soundfile, evdev, websockets, pocket_tts, torch, onnxruntime"
        if not with_voxtype:
            imports += ", pymicro_wakeword, pymicro_features"
        if with_legacy:
            imports += ", faster_whisper"
        result = subprocess.run([str(python), "-B", "-c", imports], capture_output=True, text=True,
                                env=dict(os.environ, HF_HUB_OFFLINE="1"), timeout=60, check=False)
        if result.returncode:
            problems.append("Speech runtime imports failed: " + result.stderr.strip())
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report missing requirements; no installs or desktop changes")
    parser.add_argument("--with-peek", dest="with_peek", action="store_true", help="Install Peek runtime, Voxtype recognition and computer-control tools")
    parser.add_argument("--with-voxtype", action="store_true", help="Explicitly select the default Voxtype recognition setup; implies --with-peek")
    parser.add_argument("--with-parakeet", action="store_true", help="Also download/build the optional local Parakeet recognition engine")
    parser.add_argument("--with-kokoro", action="store_true", help="Include optional Kokoro speech; implies --with-peek")
    parser.add_argument("--with-legacy-asr", action="store_true", help="Include optional Zipformer/Whisper; implies --with-peek")
    parser.add_argument("--with-desktop-input", action="store_true", help="Grant active-seat input access for desktop control; implies --with-peek")
    args = parser.parse_args(argv)
    with_peek = args.with_peek or args.with_voxtype or args.with_parakeet or args.with_kokoro or args.with_legacy_asr or args.with_desktop_input
    if platform.system() != "Linux" or (with_peek and platform.machine() != "x86_64"):
        parser.error("Requires Linux; the bundled Peek runtime currently supports x86_64 only.")
    if os.geteuid() == 0:
        parser.error("Run as your normal desktop user, without sudo. Only system package/input setup elevates.")
    for binary in ("omarchy", "omarchy-shell", "quickshell", "hyprctl", "pacman"):
        if not shutil.which(binary):
            parser.error(f"Missing {binary}. Use Omarchy with Quickshell plugin support (Quattro).")
    # Voxtype is the default recognition backend. Local Parakeet is an opt-in
    # download, but the daemon package remains installed so fresh settings are
    # always usable before a user chooses another model.
    with_voxtype = with_peek
    missing = missing_packages(with_peek, with_voxtype, args.with_parakeet)
    print("Missing Arch packages: " + (", ".join(missing) or "none"), flush=True)
    problems = []
    if args.check:
        problems.extend("Missing package: " + package for package in missing)
    else:
        if with_peek:
            # Do this before installing packages or replacing the private
            # runtime, so an active microphone session is never interrupted.
            require_peek_idle()
        if missing:
            run(["omarchy", "pkg", "add", *missing])
        if with_peek:
            # Model/build changes are separate from plugin updates, which never
            # execute this script. Do not replace a running voice runtime.
            command = [sys.executable, "-B", str(SOURCE / "peek/setup.py")]
            if args.with_parakeet:
                command.append("--with-parakeet")
            else:
                command.append("--voxtype-only")
            if args.with_kokoro:
                command.append("--with-kokoro")
            if args.with_legacy_asr:
                command.append("--with-legacy-asr")
            run(command)
        if args.with_desktop_input:
            install_input_access()
    problem = agent_problem(with_peek)
    if problem:
        problems.append(problem)
    if with_peek:
        problems.extend(runtime_problems(args.with_kokoro, args.with_legacy_asr, with_voxtype, args.with_parakeet))
        if args.with_desktop_input:
            problems.extend(input_problems())
        else:
            print("Desktop input permissions are unchanged. Use --with-desktop-input if needed.")
    for problem in problems:
        print("NEEDS SETUP: " + problem, file=sys.stderr)
    if problems:
        print("Resolve the items above, then rerun the same command with --check.", file=sys.stderr)
        return 1
    print("Dependency checks passed. No microphone or agent request was started.")
    print("Enable chat: omarchy plugin enable " + PLUGIN)
    print("Open chat:   omarchy-shell " + PLUGIN + " open")
    print("After an update, reload cached UI with: omarchy restart shell")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"Setup failed: {error}. Fix the reported problem and rerun setup.")
