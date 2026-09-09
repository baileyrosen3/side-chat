import QtQuick
import QtTest
import "../.."

Rectangle {
    width: 360; height: 450; color: "#14171d"
    QtObject {
        id: chat
        property var current: ({id: "fixture-chat", agent: "claude", bashApproval: "ask"})
        property bool connected: true
        property bool terminalOpen: false
        property var commands: []
        function request(command) { commands = commands.concat([command]) }
    }
    QtObject {
        id: host
        property color fg: "#dbe2ef"
        property color dim: "#98a2b3"
        property color line: "#444444"
        property string family: "sans-serif"
        property real textSize: 12
        function px(value) { return value }
    }
    AgentPrompt {
        id: prompt
        x: 12; y: 12; width: parent.width - 24
        host: host; chat: chat
        request: ({id: "command-1", method: "confirm", title: "Allow Bash?",
                   message: "printf fixture", allowAlwaysBash: true})
    }
    BashApprovalSettings { id: settings; x: 12; y: 235; width: parent.width - 24; chat: chat }
    TestCase {
        name: "BashApprovalControls"
        when: windowShown
        function init() {
            failOnWarning(/.?/)
            chat.current = {id: "fixture-chat", agent: "claude", bashApproval: "ask"}
            chat.connected = true; chat.terminalOpen = false; chat.commands = []
            prompt.request = {id: "command-1", method: "confirm", title: "Allow Bash?",
                              message: "printf fixture", allowAlwaysBash: true}
        }
        function test_always_button_sends_explicit_choice_and_conversation() {
            var button = findChild(prompt, "allow-bash-always")
            verify(button.visible)
            mouseClick(button)
            compare(chat.commands.length, 1)
            compare(chat.commands[0].alwaysAllowBash, true)
            compare(chat.commands[0].confirmed, true)
            compare(chat.commands[0].chatId, "fixture-chat")
        }
        function test_allow_and_deny_do_not_remember() {
            mouseClick(findChild(prompt, "allow-once"))
            compare(chat.commands[0].confirmed, true)
            verify(chat.commands[0].alwaysAllowBash === undefined)
            mouseClick(findChild(prompt, "deny-action"))
            compare(chat.commands[1].cancelled, true)
            verify(chat.commands[1].alwaysAllowBash === undefined)
        }
        function test_other_approval_has_no_always_button() {
            prompt.request = {id: "file-1", method: "confirm", title: "Allow edit?", allowAlwaysBash: false}
            verify(!findChild(prompt, "allow-bash-always").visible)
        }
        function test_settings_toggle_and_disconnect() {
            var always = findChild(settings, "bash-always")
            mouseClick(always)
            compare(chat.commands[0].mode, "always")
            compare(chat.commands[0].chatId, "fixture-chat")
            chat.current = {id: "fixture-chat", agent: "claude", bashApproval: "always"}
            verify(always.selected)
            var ask = findChild(settings, "bash-ask")
            mouseClick(ask)
            compare(chat.commands[1].mode, "ask")
            chat.connected = false
            verify(!ask.enabled); verify(!always.enabled)
        }
        function test_unsupported_agent_hides_settings() {
            chat.current = {id: "fixture-chat", agent: "omp"}
            verify(!settings.visible)
        }
        function test_long_command_keeps_decisions_visible() {
            prompt.request = {id: "long-command", method: "confirm", title: "Allow Bash?",
                              message: Array(40).fill("A command line to review before allowing.").join("\n"), allowAlwaysBash: true}
            wait(30)
            var deny = findChild(prompt, "deny-action")
            verify(deny.mapToItem(prompt, 0, deny.height).y <= prompt.height)
            verify(prompt.height < 230)
            mouseClick(deny)
            compare(chat.commands.length, 1)
            compare(chat.commands[0].cancelled, true)
        }
        function test_buttons_fit_narrow_panel() {
            wait(30)
            var always = findChild(prompt, "allow-bash-always")
            var deny = findChild(prompt, "deny-action")
            verify(always.mapToItem(prompt, always.width, 0).x < prompt.width)
            verify(deny.mapToItem(prompt, deny.width, 0).x < prompt.width)
            grabImage(parent).save("/tmp/side-chat-bash-approvals.png")
        }
    }
}
