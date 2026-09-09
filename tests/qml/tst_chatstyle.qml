import QtQuick
import QtTest
import qs.Commons
import "../.."
import "../../Theme.js" as Theme

Item {
    width: 360; height: 320
    ChatStyle { id: ui }
    Rectangle { anchors.fill: parent; color: ui.surface }
    ActionButton { id: button; x: 12; y: 12; text: "Apply"; accent: true }
    ChatField { id: field; x: 12; y: 50; width: 240; placeholderText: "Model" }
    ChatComboBox { id: combo; x: 12; y: 90; width: 240; model: ["Default", "Low", "High"] }
    ChatSwitch { id: toggle; x: 12; y: 140; Accessible.name: "Enable setting" }
    ChatSpinBox {
        id: spin; x: 12; y: 180
        from: 30; to: 200; value: 45; stepSize: 5
        textFromValue: (v, locale) => (v / 100).toFixed(2) + " s"
        valueFromText: (text, locale) => Math.round(parseFloat(text) * 100)
    }
    TestCase {
        name: "ThemedChatControls"
        when: windowShown
        function init() {
            failOnWarning(/.?/)
            Color.foreground = "#e2e6ef"; Color.background = "#14171d"; Color.accent = "#8cbbec"
            Color.popups = {background: "#20242c", text: "#e2e6ef"}
            combo.popup.close(); combo.currentIndex = 0
            toggle.checked = false; spin.value = 45
        }
        function test_existing_controls_follow_theme_changes() {
            var before = String(ui.secondary)
            Color.foreground = "#35223c"; Color.background = "#f0eaf4"; Color.accent = "#623875"
            Color.popups = {background: "#f7f2fa", text: "#35223c"}
            compare(String(ui.surface), "#f7f2fa")
            compare(String(field.color), "#35223c")
            compare(String(combo.palette.base), "#f7f2fa")
            verify(String(ui.secondary) !== before)
            compare(button.ink, ui.accentInk)
        }
        function test_accent_text_uses_contrasting_theme_color() {
            compare(ui.accentInk, ui.surface)
            verify(Theme.contrast(ui.accent, button.ink) >= 4.5)
            Color.popups = {background: "#f7f2fa", text: "#35223c"}
            Color.accent = "#623875"
            compare(ui.accentInk, ui.surface)
            verify(Theme.contrast(ui.accent, button.ink) >= 4.5)
            Color.accent = "#e4cfed"
            compare(ui.accentInk, ui.foreground)
        }
        function test_dropdown_keyboard_selection() {
            mouseClick(combo)
            tryCompare(combo.popup, "opened", true)
            keyClick(Qt.Key_Down)
            keyClick(Qt.Key_Return)
            compare(combo.currentIndex, 1)
            tryCompare(combo.popup, "opened", false)
        }
        function test_toggle_keyboard_and_disabled_state() {
            toggle.forceActiveFocus(); keyClick(Qt.Key_Space);
            compare(toggle.checked, true);
            toggle.enabled = false; keyClick(Qt.Key_Space);
            compare(toggle.checked, true); toggle.enabled = true;
        }
        function test_number_field_editing_preserves_units_and_bounds() {
            spin.forceActiveFocus(); keyClick(Qt.Key_Up); compare(spin.value, 50);
            spin.contentItem.forceActiveFocus(); keyClick(Qt.Key_A, Qt.ControlModifier);
            keyClick(Qt.Key_0); keyClick(Qt.Key_Period); keyClick(Qt.Key_7); keyClick(Qt.Key_5);
            keyClick(Qt.Key_Return); compare(spin.value, 75);
            spin.value = 200; spin.forceActiveFocus(); keyClick(Qt.Key_Up); compare(spin.value, 200);
        }
    }
}
