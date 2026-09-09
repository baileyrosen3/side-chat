import QtQuick
import QtTest
import "../.."

Item {
    width: 340
    height: 620
    Rectangle { anchors.fill: parent; color: "#20242c" }
    QtObject {
        id: chat
        property var current: ({id: "chat-1", agent: "claude"})
        property var meta: ({agent: "claude", permissionModes: {
            claude: [
                {id: "default", label: "CLI default", description: "Use the CLI's configured permissions and extensions."},
                {id: "auto", label: "Auto", description: "Let Claude review tool calls automatically. Requires availability for your account and model."},
                {id: "bypassPermissions", label: "Bypass permissions", description: "Skip Claude's permission checks. Managed restrictions still apply."}
            ],
            pi: [{id: "default", label: "CLI default", description: "Pi has no built-in approval prompts. Your installed extensions still apply."}]
        }})
        property string agentName: "Claude"
        property bool connected: true
        property bool busy: false
        property bool terminalOpen: false
        property var agentRequests: []
        property var commands: []
        property string page: "permissions"
        function request(c) { commands = commands.concat([c]) }
    }
    PermissionSettings { id: settings; x: 12; y: 12; width: parent.width - 24; chat: chat }
    SignalSpy { id: reveal; target: settings; signalName: "revealRequested" }
    TestCase {
        name: "PermissionControls"
        when: windowShown
        function init() {
            failOnWarning(/.?/)
            chat.current = {id: "chat-1", agent: "claude"}
            chat.connected = true; chat.busy = false; chat.terminalOpen = false
            chat.agentRequests = []; chat.commands = []
            reveal.clear()
        }
        function test_selection_waits_for_backend_and_sends_chat_identity() {
            var button = findChild(settings, "permission-bypassPermissions")
            mouseClick(button)
            compare(chat.commands.length, 1)
            compare(chat.commands[0].action, "permission_mode")
            compare(chat.commands[0].chatId, "chat-1")
            compare(chat.commands[0].mode, "bypassPermissions")
            compare(settings.selectedMode, "default")
            chat.current = {id: "chat-1", agent: "claude", permissionMode: "bypassPermissions"}
            compare(settings.selectedMode, "bypassPermissions")
        }
        function test_busy_disconnected_terminal_and_pending_disable_changes() {
            var button = findChild(settings, "permission-auto")
            chat.busy = true; verify(!button.enabled)
            chat.busy = false; chat.connected = false; verify(!button.enabled)
            chat.connected = true; chat.terminalOpen = true; verify(!button.enabled)
            chat.terminalOpen = false; chat.agentRequests = [{id:"pending"}]; verify(!button.enabled)
            mouseClick(button); compare(chat.commands.length, 0)
        }
        function test_agent_switch_has_its_own_choices_and_default() {
            chat.current = {id: "pi-chat", agent: "pi"}
            compare(settings.modes.length, 1)
            compare(settings.selectedMode, "default")
            chat.current = {id: "unknown-chat", agent: "unknown"}
            compare(settings.modes.length, 0)
        }
        function test_keyboard_selection_before_first_message() {
            chat.current = null
            var button = findChild(settings, "permission-auto")
            button.forceActiveFocus()
            verify(reveal.count > 0)
            compare(reveal.signalArguments[reveal.count - 1][0], button)
            keyClick(Qt.Key_Space)
            compare(chat.commands.length, 1)
            compare(chat.commands[0].chatId, null)
            compare(chat.commands[0].mode, "auto")
        }
        function test_descriptions_fit_compact_width() {
            wait(30)
            var button = findChild(settings, "permission-bypassPermissions")
            verify(button.mapToItem(settings, button.width, 0).x <= settings.width)
            verify(button.contentItem.height >= button.contentItem.implicitHeight)
            grabImage(parent).save("/tmp/side-chat-permissions.png")
        }
    }
}
