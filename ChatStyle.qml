import QtQuick
import qs.Commons
import "Theme.js" as Theme

QtObject {
    readonly property color foreground: Color.popups.text
    readonly property color surface: Color.popups.background
    readonly property color accent: Color.accent
    readonly property color secondary: Theme.mix(surface, accent, 0.09)
    readonly property color emphasis: Color.accent
    readonly property color danger: Color.urgent
    readonly property color muted: Theme.mix(foreground, surface, 0.26)
    readonly property color accentInk: Theme.readable(accent, foreground, surface)
    readonly property color line: Theme.mix(surface, foreground, 0.18)
    readonly property color border: Theme.mix(surface, foreground, 0.36)
    readonly property color field: Theme.mix(surface, foreground, 0.035)
    readonly property string family: Style.font.family
    readonly property int body: Style.font.body
    readonly property int small: Math.max(10, body - 1)
    readonly property int caption: Math.max(10, body - 2)
    readonly property int controlHeight: Math.max(Style.space(26), body + Style.space(10))
    readonly property int radius: 0
    readonly property real stroke: Math.max(1, Style.space(1.5))
    readonly property real shadow: Style.space(2)
}
