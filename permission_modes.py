"""Conversation-scoped CLI permission choices; never edit the user's CLI config."""
import json
from pathlib import Path


def choice(identity, label, description):
    return {"id": identity, "label": label, "description": description}


DEFAULT = choice("default", "CLI default", "Use the CLI's configured permissions and extensions.")
MODES = {
    "codex": [DEFAULT,
        choice("read-only", "Read-only", "Read-only command sandbox, with no approval escalation. External tools keep their own permissions."),
        choice("workspace", "Workspace", "Allow work in the project sandbox. Ask you for additional access."),
        choice("auto-review", "Auto review", "Use the project sandbox and let Codex review requests for additional access."),
        choice("full-access", "Full access", "Run commands with no sandbox or approval prompts.")],
    "claude": [DEFAULT,
        choice("manual", "Ask", "Use Claude's manual approval mode and existing permission rules."),
        choice("acceptEdits", "Accept edits", "Automatically accept file edits. Other tools follow Claude's permission rules."),
        choice("plan", "Plan", "Explore and plan with Claude's plan mode before making changes."),
        choice("auto", "Auto", "Let Claude review tool calls automatically. Requires Auto mode availability for your account and model."),
        choice("bypassPermissions", "Bypass permissions", "Skip Claude's permission checks. Managed restrictions still apply."),
        choice("dontAsk", "Don't ask", "Deny tools that are not already approved by Claude's permission rules.")],
    "omp": [DEFAULT,
        choice("always-ask", "Ask", "Allow reads; ask before writes and execution. Per-tool rules still apply."),
        choice("write", "Allow writes", "Allow reads and writes; ask before execution. Per-tool rules still apply."),
        choice("yolo", "YOLO", "Automatically allow tools unless your OMP per-tool rules require a prompt or denial.")],
    "pi": [choice("default", "CLI default", "Pi has no built-in approval prompts. Your installed extensions still apply."),
        choice("ask", "Ask before tools", "Side Chat asks before each Pi tool call through a permission extension. This does not add a sandbox.")],
    "opencode": [choice("default", "Chat only", "Tools are disabled in Side Chat's text integration."),
        choice("auto", "Auto approve", "Enable tools and automatically approve requests unless your OpenCode rules deny them. Inline approval prompts are not available here.")],
}


def modes_for(agent):
    return MODES.get(agent, [])


def validate_mode(agent, mode):
    if not isinstance(mode, str) or not any(m["id"] == mode for m in modes_for(agent)):
        raise ValueError("This permission mode is not supported for the selected CLI.")
    return mode


def session_options(chat):
    return dict(chat["options"], _permission_mode=chat.get("permissionMode", "default"))


def codex_permissions(mode):
    validate_mode("codex", mode)
    if mode == "default":
        return {}
    sandbox, policy = {
        "read-only": ("read-only", "never"),
        "workspace": ("workspace-write", "on-request"),
        "auto-review": ("workspace-write", "on-request"),
        "full-access": ("danger-full-access", "never"),
    }[mode]
    return {"sandbox": sandbox, "approvalPolicy": policy,
            "approvalsReviewer": "auto_review" if mode == "auto-review" else "user"}


def _toml_policy(value):
    if isinstance(value, dict):
        return "{" + ", ".join(json.dumps(k) + "=" + _toml_policy(v) for k, v in value.items()) + "}"
    return json.dumps(value)


def permission_args(agent, mode, defaults=None):
    """Use the same override when starting, reconnecting, or handing off to a terminal."""
    validate_mode(agent, mode)
    if mode == "default":
        if agent == "codex" and defaults:
            return ["-c", "approval_policy=" + _toml_policy(defaults["approvalPolicy"]),
                    "-c", "approvals_reviewer=" + _toml_policy(defaults.get("approvalsReviewer", "user"))]
        return []
    if agent == "codex":
        params = codex_permissions(mode)
        return ["--sandbox", params["sandbox"], "--ask-for-approval", params["approvalPolicy"],
                "-c", 'approvals_reviewer="' + params["approvalsReviewer"] + '"']
    if agent == "claude":
        # `default` is the older, widely supported spelling of manual mode.
        return (["--dangerously-skip-permissions"] if mode == "bypassPermissions" else
                ["--permission-mode", "default" if mode == "manual" else mode])
    if agent == "omp":
        return ["--approval-mode", mode]
    if agent == "pi":
        return ["--extension", str(Path(__file__).with_name("agents") / "pi_permissions.ts")]
    if agent == "opencode":
        return ["--auto"]
    return []
