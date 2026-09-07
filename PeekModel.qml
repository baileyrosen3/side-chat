// SPDX-License-Identifier: GPL-3.0-or-later
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick3D
import qs.Commons

Node {
    id: root
    required property var motion
    readonly property var m: motion
    readonly property real nod: m.gesture === "nod" ? Math.sin(m.progress*Math.PI*4)*m.pulse : 0
    RoundedGeometry { id: shell; corner: 28 }
    RoundedGeometry { id: rounded; corner: 38 }
    SculptGeometry { id: sphere }
    PrincipledMaterial { id: ceramic; baseColor: Color.foreground; metalness: .08; roughness: .32; clearcoatAmount: .35; clearcoatRoughnessAmount: .25 }
    PrincipledMaterial { id: dark; baseColor: Color.background; metalness: .4; roughness: .36 }
    PrincipledMaterial { id: trim; baseColor: Color.accent; metalness: .72; roughness: .32 }
    PrincipledMaterial { id: rubber; baseColor: Qt.tint(Color.background,Qt.rgba(Color.foreground.r,Color.foreground.g,Color.foreground.b,.12)); roughness: .84 }
    PrincipledMaterial { id: light; baseColor: root.m.action === "error" ? Color.urgent : Color.accent; emissiveFactor: Qt.vector3d(baseColor.r*.3,baseColor.g*.3,baseColor.b*.3); roughness: .25 }
    RobotFace { id: face; motion: root.motion }

    Node {
        x: -78*(1-root.m.arrival)
        Model { geometry: rounded; position: Qt.vector3d(-54,-26,-12); eulerRotation.z: -20; scale: Qt.vector3d(.37,.58,.35); materials: [ceramic] }
        Model { geometry: sphere; position: Qt.vector3d(-28,-8,-3); scale: Qt.vector3d(.20,.20,.20); materials: [trim] }
        Model { geometry: rounded; position: Qt.vector3d(-37,-10,-7); eulerRotation.z: -45; scale: Qt.vector3d(.16,.39,.19); materials: [dark] }
        Node {
            id: head
            x: -17+root.m.lean*23+root.m.shake*2
            y: 15+root.m.breathe*1.25+root.m.joy*8+root.m.waking*5-root.m.landing*5+root.m.lift*7
            eulerRotation: Qt.vector3d(root.m.pitch+root.m.greeting*6+root.m.energy*4+root.m.sleep*12+root.nod*9,root.m.yaw+root.m.shake*7,-7-root.m.lean*4+root.m.attention*11+root.m.work*2+root.m.lift*10+root.m.wave*2)
            // A wide ceramic pebble with one continuous face. Every material uses live theme roles.
            Model { geometry: shell; scale: Qt.vector3d(.84,.67,.48); materials: [ceramic] }
            Model { geometry: shell; position: Qt.vector3d(0,1,23); scale: Qt.vector3d(.76,.57,.10); materials: [trim] }
            Model { geometry: shell; position: Qt.vector3d(0,1,27); scale: Qt.vector3d(.735,.54,.08); materials: [dark] }
            Model { geometry: shell; position: Qt.vector3d(0,1,31); scale: Qt.vector3d(.70,.50,.035); materials: [face] }
            // Off-centre antenna: an unmistakable silhouette, with a soft tip.
            Node {
                position: Qt.vector3d(22,30,0)
                eulerRotation.z: -18+root.m.wave*12+root.m.scan*8+root.m.joy*12-root.m.sleep*25+root.m.warming*7
                Model { geometry: sphere; scale: Qt.vector3d(.095,.08,.09); materials: [dark] }
                Model { geometry: rounded; y: 7; scale: Qt.vector3d(.027,.15,.03); materials: [trim] }
                Node {
                    y: 14; eulerRotation.z: -28
                    Model { geometry: rounded; y: 4; scale: Qt.vector3d(.027,.09,.03); materials: [trim] }
                    Model { geometry: sphere; y: 10; scale: Qt.vector3d(.094,.094,.094); materials: [light] }
                }
            }
            Repeater3D {
                model: [-1,1]
                Node {
                    id: earPod
                    required property int modelData
                    position: Qt.vector3d(modelData*41,1,-2)
                    eulerRotation.z: modelData*(root.m.greeting*8+root.m.joy*14-root.m.sleep*9)
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
        Repeater3D {
            model: [43,-45]
            Node {
                id: hand
                required property int modelData
                position: Qt.vector3d(-32+(modelData>0 ? root.m.greeting*10 : 0),modelData+(modelData>0 ? root.m.greeting*13 : -root.m.work),44)
                eulerRotation.z: modelData>0 ? root.m.wave*28 : root.m.work*5
                Model { geometry: rounded; x: -6; z: -5; scale: Qt.vector3d(.15,.24,.18); materials: [rubber] }
                Repeater3D {
                    model: 3
                    Node {
                        required property int index
                        y: (index-1)*6.5
                        x: root.m.animated && (root.m.action === "thinking" || root.m.action === "acting") ? Math.max(0,Math.sin(root.m.cycle*6-index*.9))*2 : 0
                        eulerRotation.z: hand.modelData>0 ? root.m.greeting*(index-1)*7 : 0
                        Model { geometry: rounded; x: 1; scale: Qt.vector3d(.205,.057,.13); materials: [ceramic] }
                        Model { geometry: rounded; position: Qt.vector3d(7,0,6); scale: Qt.vector3d(.042,.026,.009); materials: [trim] }
                    }
                }
                Model { geometry: rounded; position: Qt.vector3d(5,-12,1); eulerRotation.z: 32; scale: Qt.vector3d(.07,.11,.11); materials: [ceramic] }
            }
        }
    }
}
