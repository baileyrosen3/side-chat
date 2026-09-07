// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick3D

CustomMaterial {
    property color tint: "#a95a31"
    property color secondary: "#efb36d"
    property real surfaceStyle: 0
    property real clock: 0
    property real energy: 0
    property real glowAmount: 1
    property real opacityAmount: 1
    property real swim: 0
    property real seed: 0
    property real softness: .7
    sourceBlend: opacityAmount < 1 ? CustomMaterial.SrcAlpha : CustomMaterial.NoBlend
    destinationBlend: opacityAmount < 1 ? CustomMaterial.OneMinusSrcAlpha : CustomMaterial.NoBlend
    cullMode: CustomMaterial.NoCulling
    vertexShader: "assets/companion/surface.vert"
    fragmentShader: "assets/companion/surface.frag"
}
