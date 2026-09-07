import QtQuick
import QtTest
import "../.."
import "../../WindowBorder.js" as Parser

Item {
    width: 360; height: 360
    DrawerSurface {
        id: surface
        width: 200; height: 200
        fill: "black"
    }
    QtObject {
        id: chat
        property var meta: ({})
        property bool connected: true
        property var commands: []
        function request(command) {
            commands = commands.concat([command])
            meta = {appearance: command.settings}
        }
    }
    LookSettings { id: settings; y: 220; width: 340; chat: chat }
    TestCase {
        name: "PanelOutline"
        when: windowShown
        function init() {
            failOnWarning(/.?/)
            surface.outlineEnabled = true
            surface.keyboardFocus = false
            surface.borderColors = [Qt.rgba(1, 0, 0, 1)]
            surface.borderAngle = 0
            surface.borderWidth = 4
            chat.meta = {}; chat.connected = true; chat.commands = []
        }
        function shot() {
            surface.requestPaint()
            wait(80)
            return grabImage(surface)
        }
        function test_argb_and_angles() {
            var solid = Parser.parseGradient("eec8b89a 0deg")
            compare(solid.colors.length, 1)
            fuzzyCompare(solid.colors[0].r, 200 / 255, 0.0001)
            fuzzyCompare(solid.colors[0].g, 184 / 255, 0.0001)
            fuzzyCompare(solid.colors[0].b, 154 / 255, 0.0001)
            fuzzyCompare(solid.colors[0].a, 238 / 255, 0.0001)
            var gradient = Parser.parseGradient("  FFFF0000\t800000ff -45.5deg \n")
            compare(gradient.angle, -45.5)
            compare(gradient.colors[0], Qt.rgba(1, 0, 0, 1))
            fuzzyCompare(gradient.colors[1].a, 128 / 255, 0.0001)
            compare(Parser.parseGradient("00000000").colors[0].a, 0)
            compare(Parser.parseGradient(Array(33).join("ffffffff ")).colors.length, 32)
        }
        function test_invalid_gradients() {
            for (var value of [null, {}, "", "0deg", "badcolor 0deg", "#c8b89a", "ffffff",
                               "ffff0000 0deg ff0000ff", "ffff0000 NaNdeg", Array(34).join("ffffffff ")])
                compare(Parser.parseGradient(value), null)
        }
        function test_width_validation() {
            compare(Parser.parseWidth(0), 0)
            compare(Parser.parseWidth(3), 3)
            compare(Parser.parseWidth(999), 100)
            for (var value of [null, undefined, "1", -1, NaN, Infinity])
                compare(Parser.parseWidth(value), -1)
        }
        function test_full_width_stays_inside_silhouette() {
            var rendered = shot()
            compare(rendered.pixel(100, 20), Qt.rgba(1, 0, 0, 1))
            compare(rendered.pixel(100, 23), Qt.rgba(1, 0, 0, 1))
            compare(rendered.pixel(100, 24), Qt.rgba(0, 0, 0, 1))
            compare(rendered.pixel(199, 100), Qt.rgba(1, 0, 0, 1))
            compare(rendered.pixel(0, 100), Qt.rgba(0, 0, 0, 1))
            compare(rendered.pixel(1, 100), Qt.rgba(0, 0, 0, 1))
            surface.borderWidth = 1
            rendered = shot()
            compare(rendered.pixel(100, 20), Qt.rgba(1, 0, 0, 1))
            compare(rendered.pixel(100, 21), Qt.rgba(0, 0, 0, 1))
        }
        function test_alpha_and_gradient_direction_repaint() {
            surface.borderColors = Parser.parseGradient("80ff0000").colors
            var rendered = shot()
            fuzzyCompare(rendered.pixel(100, 20).r, 128 / 255, 0.01)
            surface.borderColors = Parser.parseGradient("ffff0000 ff0000ff").colors
            rendered = shot()
            verify(rendered.pixel(30, 21).r > rendered.pixel(170, 21).r)
            verify(rendered.pixel(170, 21).b > rendered.pixel(30, 21).b)
            surface.borderAngle = 180
            rendered = shot()
            verify(rendered.pixel(30, 21).b > rendered.pixel(170, 21).b)
            surface.borderAngle = 90
            rendered = shot()
            verify(rendered.pixel(198, 50).r > rendered.pixel(198, 150).r)
        }
        function test_keyboard_focus_preserves_desktop_colors_and_gradient() {
            surface.borderColors = Parser.parseGradient("eec8b89a 800000ff 45deg").colors
            surface.borderAngle = 45
            var unfocused = shot()
            surface.keyboardFocus = true
            verify(unfocused.equals(shot()), "Pinning must not replace the desktop border with the UI accent")
            surface.outlineEnabled = false
            verify(unfocused.equals(shot()), "The focus outline must retain the same desktop styling")
        }
        function test_toggle_and_zero_width_keep_keyboard_focus_visible() {
            surface.outlineEnabled = false
            compare(shot().pixel(100, 20), Qt.rgba(0, 0, 0, 1))
            surface.borderWidth = 0
            surface.keyboardFocus = true
            compare(shot().pixel(100, 20), Qt.rgba(1, 0, 0, 1))
            surface.borderColors = [Qt.rgba(0, 0, 1, 1)]
            compare(shot().pixel(100, 20), Qt.rgba(0, 0, 1, 1))
            surface.keyboardFocus = false
            surface.outlineEnabled = true
            compare(shot().pixel(100, 20), Qt.rgba(0, 0, 0, 1))
        }
        function test_settings_toggle_reset_and_keyboard() {
            var toggle = findChild(settings, "outline-toggle")
            var reset = findChild(settings, "reset-look")
            compare(toggle.text, "On")
            mouseClick(toggle)
            compare(toggle.text, "Off")
            compare(toggle.checked, false)
            compare(chat.commands[0].settings.outline, false)
            reset.forceActiveFocus(); keyClick(Qt.Key_Space)
            compare(toggle.text, "On")
            compare(toggle.checked, true)
            toggle.forceActiveFocus(); keyClick(Qt.Key_Space)
            compare(toggle.text, "Off")
            compare(chat.commands.length, 3)
            grabImage(settings).save("/tmp/side-chat-outline-settings.png")
        }
    }
}
