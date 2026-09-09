// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Commons

PanelWindow {
    id: window

    required property var chat
    readonly property bool selected: chat.companionScreen === screen.name
    readonly property bool activeCompanion: chat.peek.enabled && selected
    property real dragOrigin: 0
    property real dragOffset: 0
    property real pendingPosition: -1
    readonly property real savedPosition: chat.peek.companionPosition === undefined ? 0.16 : chat.peek.companionPosition
    readonly property real placementHeight: Style.space(248)
    // Expanding the attached controls keeps Peek at the same screen position.
    readonly property real restingBottom: Math.max(Style.space(16), Math.min(screen.height - height - Style.space(32), (pendingPosition >= 0 ? pendingPosition : savedPosition) * (screen.height - placementHeight) + placementHeight - height))

    onSavedPositionChanged: {
        if (Math.abs(savedPosition - pendingPosition) < 0.0001) {
            pendingPosition = -1;
        }
    }
    implicitWidth: surface.implicitWidth
    implicitHeight: surface.implicitHeight
    margins.left: chat.openScreen === screen.name ? Math.min(chat.panelWidth, screen.width - width) : 0
    margins.bottom: Math.max(Style.space(8), Math.min(screen.height - height - Style.space(28), restingBottom + dragOffset))
    color: "transparent"
    // Keep the native window alive. Qt Quick 3D crashes when a retained View3D
    // is attached to a recreated Quickshell window after hiding/showing it.
    // Hidden mode has no painted content or input region.
    visible: true
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "omarchy-peek-companion"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: activeCompanion && (surface.controlsPinned || surface.details.expanded) ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

    anchors {
        left: true
        bottom: true
    }

    CompanionCursor {
        id: cursor
        enabled: window.activeCompanion && !chat.peek.reducedMotion
                 && (chat.peek.expressiveness === undefined || chat.peek.expressiveness > 0)
                 && chat.peek.stage !== "standby" && chat.peek.stage !== "off"
    }

    CompanionSurface {
        id: surface

        anchors.fill: parent
        chat: window.chat
        present: window.activeCompanion
        desktopPointer: cursor.valid ? cursor.position : null
        // Layer-shell windows do not reliably expose their global Qt position.
        // Hyprland cursor coordinates and screen geometry use logical pixels.
        desktopOrigin: Qt.point(window.screen.x + window.margins.left,
                                window.screen.y + window.screen.height - window.margins.bottom - window.height)
        gazeDistance: Math.max(Style.space(200), Math.min(window.screen.width, window.screen.height) * 0.35)
        objectName: "peek-surface"
        onDragStarted: window.dragOrigin = window.margins.bottom
        onDragMoved: (delta) => {
            return window.dragOffset = window.dragOrigin - delta - window.restingBottom;
        }
        onDragFinished: {
            var position = Math.max(0, Math.min(1, (window.margins.bottom + window.height - window.placementHeight) / Math.max(1, window.screen.height - window.placementHeight)));
            window.pendingPosition = position;
            window.dragOffset = 0;
            chat.request({
                "action": "peek_settings",
                "settings": {
                    "companionPosition": position
                }
            });
            if(Math.abs(window.savedPosition-position)<.0001) window.pendingPosition=-1
        }
    }

    Connections {
        function onCompanionControlsRequested() {
            if (window.selected)
                surface.showControls();

        }

        function onErrorChanged() {
            if (chat.error)
                window.pendingPosition = -1;

        }

        target: chat
    }

    mask: Region {
        Region {
            x: surface.bodyRegion.x
            y: surface.bodyRegion.y
            width: surface.interactive ? surface.bodyRegion.width : 0
            height: surface.bodyRegion.height
        }
        Region {
            x: surface.panelRegion.x
            y: surface.panelRegion.y
            width: surface.interactive && surface.panelRegion.visible ? surface.panelRegion.width : 0
            height: surface.panelRegion.height
        }

    }

}
