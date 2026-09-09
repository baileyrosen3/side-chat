// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick3D
import QtQuick3D.Helpers

View3D {
    id: root
    property string mood: "idle"
    property real inputLevel: 0
    property real outputLevel: 0
    property bool reducedMotion: false
    property real gazeX: 0
    property real gazeY: 0
    property bool tracking: false
    property bool engaged: false
    property real expressiveness: 1
    property real completedAt: 0
    property bool dragging: false
    property bool voiceReady: false
    property bool hearing: false
    // A negative value uses the standalone preview's entrance animation.
    property real revealProgress: -1
    readonly property string characterId: "peek"
    readonly property string characterName: "Peek"
    readonly property string currentAction: driver.action
    readonly property alias animation: driver
    readonly property color expressionColor: character.faceColor
    function greet() { driver.greet(); }
    function preview(action) { driver.preview(action); }

    CompanionMotion {
        id: driver
        mood: root.mood; inputLevel: root.inputLevel; outputLevel: root.outputLevel
        reducedMotion: root.reducedMotion; expressiveness: root.expressiveness
        gazeX: root.gazeX; gazeY: root.gazeY; tracking: root.tracking
        engaged: root.engaged; completedAt: root.completedAt; dragging: root.dragging
        revealProgress: root.revealProgress
        voiceReady: root.voiceReady; hearing: root.hearing
    }
    environment: ExtendedSceneEnvironment {
        backgroundMode: SceneEnvironment.Transparent
        antialiasingMode: SceneEnvironment.MSAA
        antialiasingQuality: SceneEnvironment.Medium
        lightProbe: Texture { source: "assets/companion/studio.hdr" }
        probeExposure: .32
        tonemapMode: SceneEnvironment.TonemapModeAces
        specularAAEnabled: true
        // Contact shading anchors the ceramic shell, joints, and face rim.
        aoStrength: .65; aoDistance: 8; aoSoftness: 70; aoBias: .2
        ditheringEnabled: true
    }
    camera: sceneCamera
    OrthographicCamera {
        id: sceneCamera
        position: Qt.vector3d(0,0,400)
        horizontalMagnification: Math.max(.01,root.width/200)
        verticalMagnification: Math.max(.01,root.height/200)
    }
    DirectionalLight { eulerRotation: Qt.vector3d(-32,-32,0); brightness: 1.0; color: "#ffffff"; ambientColor: "#151515" }
    DirectionalLight { eulerRotation: Qt.vector3d(8,125,0); brightness: 1.1; color: "#ffffff" }
    DirectionalLight { eulerRotation: Qt.vector3d(55,20,0); brightness: .14; color: "#ffffff" }
    PeekModel { id: character; motion: driver }
}
