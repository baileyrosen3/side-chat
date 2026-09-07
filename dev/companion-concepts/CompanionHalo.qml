// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick3D
CustomMaterial {
    shadingMode: CustomMaterial.Unshaded
    property color tint: "#ffc989"
    property real strength: .6
    sourceBlend: CustomMaterial.SrcAlpha
    destinationBlend: CustomMaterial.One
    cullMode: CustomMaterial.BackFaceCulling
    vertexShader: "assets/companion/halo.vert"
    fragmentShader: "assets/companion/halo.frag"
}
