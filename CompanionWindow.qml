// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Commons

PanelWindow {
    id: window

    required property var chat
    readonly property bool selected: chat.companionScreen === screen.name
    readonly property bool activeCompanion: chat.jarvis.enabled && selected
    property real dragOrigin: 0
    property real dragOffset: 0
    property real pendingPosition: -1
    readonly property real savedPosition: chat.jarvis.companionPosition === undefined ? 0.16 : chat.jarvis.companionPosition
    readonly property real restingBottom: Math.max(Style.space(16), Math.min(screen.height - height - Style.space(32), (pendingPosition >= 0 ? pendingPosition : savedPosition) * (screen.height - height)))

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
    WlrLayershell.namespace: "omarchy-jarvis-companion"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: activeCompanion && surface.controlsPinned ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

    anchors {
        left: true
        bottom: true
    }

    CompanionSurface {
        id: surface

        anchors.fill: parent
        chat: window.chat
        visible: window.activeCompanion
        objectName: "jarvis-surface"
        onDragStarted: window.dragOrigin = window.margins.bottom
        onDragMoved: (delta) => {
            return window.dragOffset = window.dragOrigin - delta - window.restingBottom;
        }
        onDragFinished: {
            var position = Math.max(0, Math.min(1, window.margins.bottom / Math.max(1, window.screen.height - window.height)));
            window.pendingPosition = position;
            window.dragOffset = 0;
            chat.request({
                "action": "jarvis_settings",
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
            width: window.activeCompanion ? surface.bodyRegion.width : 0
            height: surface.bodyRegion.height
        }
        Region {
            x: surface.statusRegion.x
            y: surface.statusRegion.y
            width: window.activeCompanion ? surface.statusRegion.width : 0
            height: surface.statusRegion.height
        }

        Region {
            x: surface.controlsRegion.x
            y: surface.controlsRegion.y
            width: window.activeCompanion && surface.controlsRegion.visible ? surface.controlsRegion.width : 0
            height: surface.controlsRegion.height
        }

        Region {
            x: surface.captionRegion.x
            y: surface.captionRegion.y
            width: window.activeCompanion && surface.captionRegion.visible ? surface.captionRegion.width : 0
            height: surface.captionRegion.height
        }

    }

}
