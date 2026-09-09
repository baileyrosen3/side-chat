// SPDX-License-Identifier: GPL-3.0-or-later
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick3D
import qs.Commons

Node {
    id: root
    required property var motion
    readonly property var m: motion
    readonly property color faceColor: face.eyeColor
    function smooth(value) { var t=Math.max(0,Math.min(1,value));return t*t*(3-2*t) }
    // Hands find the edge first and keep their grip while the head retreats.
    readonly property real handReveal: smooth(m.reveal/.55)
    readonly property real headReveal: smooth((m.reveal-.10)/.90)
    readonly property real nod: m.gesture === "nod" ? Math.sin(m.progress*Math.PI*4)*m.pulse : 0
    RoundedGeometry { id: shell; corner: 28 }
    RoundedGeometry { id: rounded; corner: 38 }
    SculptGeometry { id: sphere }
    PrincipledMaterial { id: ceramic; baseColor: Color.foreground; metalness: .08; roughness: .32; clearcoatAmount: .35; clearcoatRoughnessAmount: .25 }
    PrincipledMaterial { id: dark; baseColor: Color.background; metalness: .4; roughness: .36 }
    PrincipledMaterial { id: trim; baseColor: face.signalTint; metalness: .58; roughness: .30; emissiveFactor: Qt.vector3d(baseColor.r*.12,baseColor.g*.12,baseColor.b*.12) }
    PrincipledMaterial { id: rubber; baseColor: Qt.tint(Color.background,Qt.rgba(Color.foreground.r,Color.foreground.g,Color.foreground.b,.12)); roughness: .84 }
    PrincipledMaterial { id: light; baseColor: face.eyeColor; readonly property real glow: .65+root.m.energy*.6+root.m.readySignal*.4; emissiveFactor: Qt.vector3d(baseColor.r*glow,baseColor.g*glow,baseColor.b*glow); roughness: .25 }
    RobotFace { id: face; motion: root.motion }

    Node {
        x: -112*(1-root.headReveal)
        Model { geometry: rounded; position: Qt.vector3d(-54,-26,-12); eulerRotation.z: -20; scale: Qt.vector3d(.37,.58,.35); materials: [ceramic] }
        Model { geometry: sphere; position: Qt.vector3d(-28,-8,-3); scale: Qt.vector3d(.20,.20,.20); materials: [trim] }
        Model { geometry: rounded; position: Qt.vector3d(-37,-10,-7); eulerRotation.z: -45; scale: Qt.vector3d(.16,.39,.19); materials: [dark] }
        Node {
            id: head
            x: -17+root.m.lean*23+root.m.shake*2
            y: 15+root.m.breathe*1.8+root.m.joy*7+root.m.celebration*3+root.m.waking*7+root.m.readySignal*7+root.m.listenRock*2-root.m.landing*5+root.m.lift*7
            eulerRotation: Qt.vector3d(root.m.pitch+root.m.greeting*6+root.m.energy*3+root.m.sleep*12+root.nod*9+root.m.readyNod*8+root.m.talkNod*5+root.m.hearingNod*5,root.m.yaw+root.m.shake*9,-7-root.m.lean*4+root.m.attention*8+root.m.work*3+root.m.lift*10+root.m.wave*3+root.m.listenRock*4+root.m.poseTilt-8*(1-root.headReveal))
            // A wide ceramic pebble with one continuous face. Every material uses live theme roles.
            Model { geometry: shell; scale: Qt.vector3d(.84,.67,.48); materials: [ceramic] }
            Model { geometry: shell; position: Qt.vector3d(0,1,23); scale: Qt.vector3d(.76,.57,.10); materials: [trim] }
            Model { geometry: shell; position: Qt.vector3d(0,1,27); scale: Qt.vector3d(.735,.54,.08); materials: [dark] }
            Model { geometry: shell; position: Qt.vector3d(0,1,31); scale: Qt.vector3d(.70,.50,.035); materials: [face] }
            // Off-centre antenna: an unmistakable silhouette, with a soft tip.
            Node {
                position: Qt.vector3d(22,30,0)
                eulerRotation.z: -18+root.m.wave*18+root.m.scan*13+root.m.joy*17+root.m.readyNod*12+root.m.listenRock*10-root.m.sleep*25+root.m.warming*12-10*Math.sin(root.headReveal*Math.PI)
                Model { geometry: sphere; scale: Qt.vector3d(.095,.08,.09); materials: [dark] }
                Model { geometry: rounded; y: 7; scale: Qt.vector3d(.027,.15,.03); materials: [trim] }
                Node {
                    y: 14; eulerRotation.z: -28
                    Model { geometry: rounded; y: 4; scale: Qt.vector3d(.027,.09,.03); materials: [trim] }
                    Model { geometry: sphere; y: 10; readonly property real size: .094*(1+root.m.energy*.22+root.m.readySignal*.18); scale: Qt.vector3d(size,size,size); materials: [light] }
                }
            }
            Repeater3D {
                model: [-1,1]
                Node {
                    id: earPod
                    required property int modelData
                    position: Qt.vector3d(modelData*41,1,-2)
                    eulerRotation.z: modelData*(root.m.greeting*12+root.m.joy*18+root.m.attentive*5+root.m.readySignal*12-root.m.sleep*9)
                    Model { geometry: sphere; scale: Qt.vector3d(.13,.28,.28); materials: [dark] }
                    Model { geometry: sphere; x: earPod.modelData*3; scale: Qt.vector3d(.08,.20,.20); materials: [trim] }
                    Model { geometry: sphere; x: earPod.modelData*5; scale: Qt.vector3d(.06,.13,.13); materials: [ceramic] }
                }
            }
            // Small inset badge and asymmetrical speaker vents, kept off the face.
            Model { geometry: rounded; position: Qt.vector3d(-6,-29,23); scale: Qt.vector3d(.11,.035,.02); materials: [trim] }
            Repeater3D {
                model: 3
                Model { required property int index; geometry: rounded; position: Qt.vector3d(15+index*4,-28,23); scale: Qt.vector3d(.014,.03,.015); materials: [dark] }
            }
        }
    }
    Repeater3D {
        model: [43,-45]
        Node {
            id: hand
            required property int modelData
            position: Qt.vector3d(-32-24*(1-root.handReveal)+(modelData>0 ? root.m.greeting*10+root.m.readySignal*4 : 0),modelData+(modelData>0 ? root.m.greeting*13+root.m.joy*6 : -root.m.work),44)
            eulerRotation.z: modelData>0 ? root.m.wave*32+root.m.readyNod*8 : root.m.work*7
            Model { geometry: rounded; x: -6; z: -5; scale: Qt.vector3d(.15,.24,.18); materials: [rubber] }
            Repeater3D {
                model: 3
                Node {
                    required property int index
                    y: (index-1)*6.5
                    x: root.m.animated && (root.m.action === "thinking" || root.m.action === "acting") ? Math.max(0,Math.sin(root.m.cycle*6-index*.9))*3.5 : root.m.attentive*root.m.energy*(index+1)*.45
                    eulerRotation.z: hand.modelData>0 ? root.m.greeting*(index-1)*7 : 0
                    Model { geometry: rounded; x: 1; scale: Qt.vector3d(.205,.057,.13); materials: [ceramic] }
                    Model { geometry: rounded; position: Qt.vector3d(7,0,6); scale: Qt.vector3d(.042,.026,.009); materials: [trim] }
                }
            }
            Model { geometry: rounded; position: Qt.vector3d(5,-12,1); eulerRotation.z: 32; scale: Qt.vector3d(.07,.11,.11); materials: [ceramic] }
        }
    }
}
