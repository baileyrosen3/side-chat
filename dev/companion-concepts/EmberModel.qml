// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick3D

Node {
    id: root
    required property var motion
    readonly property var m: motion
    SculptGeometry { id: sphere }
    SculptGeometry { id: head; shape: "head" }
    SculptGeometry { id: ear; shape: "ear" }
    CompanionMaterial { id: fur; tint: "#9e4321"; secondary: "#edac60" }
    CompanionMaterial { id: lightFur; tint: "#b45b2c"; secondary: "#ffd193" }
    CompanionMaterial { id: cream; tint: "#c6b69b"; secondary: "#fff0d6" }
    CompanionMaterial { id: darkFur; tint: "#251b1b"; secondary: "#725141" }
    PrincipledMaterial { id: innerEar; baseColor: "#73443d"; roughness: .87 }
    PrincipledMaterial { id: eyes; baseColor: "#0d1015"; roughness: .085; clearcoatAmount: 1; clearcoatRoughnessAmount: .07 }
    PrincipledMaterial { id: iris; baseColor: "#a66d30"; metalness: .25; roughness: .16 }
    PrincipledMaterial { id: nose; baseColor: "#221b1c"; roughness: .36 }
    PrincipledMaterial { id: ivory; baseColor: "#c8bca5"; roughness: .48 }

    Node {
        x: -76*(1-root.m.arrival)
        Model { geometry: sphere; position: Qt.vector3d(-42,-28,-15); eulerRotation.z: -13; scale: Qt.vector3d(.42,.64,.38); materials: [fur] }
        Model { geometry: sphere; position: Qt.vector3d(-25,-16,-3); eulerRotation.z: -28; scale: Qt.vector3d(.26,.36,.27); materials: [cream] }
        Node {
            position: Qt.vector3d(-32,-56,-15)
            eulerRotation.z: -52+root.m.breathe*7+root.m.wave*10+root.m.joy*30+root.m.work*12-root.m.sleep*30+root.m.lift*22
            Model { geometry: head; position: Qt.vector3d(0,21,0); scale: Qt.vector3d(.30,.69,.27); materials: [fur] }
            Model { geometry: head; position: Qt.vector3d(0,48,0); scale: Qt.vector3d(.215,.24,.195); materials: [cream] }
        }
        Node {
            x: -14+root.m.lean*20+root.m.shake*3
            y: 12+root.m.breathe*.8+root.m.joy*9+root.m.waking*6+root.m.lift*6-root.m.landing*5
            eulerRotation: Qt.vector3d(root.m.pitch+root.m.sleep*14+root.m.energy*2,root.m.yaw,-10-root.m.lean*3+root.m.attention*14+root.m.greeting*6+root.m.work*2)
            Model { geometry: head; scale: Qt.vector3d(.62,.56,.44); materials: [fur] }
            Model { geometry: sphere; position: Qt.vector3d(0,8,7); scale: Qt.vector3d(.50,.43,.36); materials: [lightFur] }
            Repeater3D {
                model: [-1,1]
                Node {
                    id: side
                    required property int modelData
                    Node {
                        position: Qt.vector3d(side.modelData*19,18,-2)
                        eulerRotation.z: side.modelData*(-15-root.m.sleep*25-root.m.lift*12+root.m.energy*9+root.m.waking*10)-root.m.scan*11+root.m.shake*12
                        Model { geometry: ear; scale: Qt.vector3d(.38,.44,.47); materials: [darkFur] }
                        Model { geometry: ear; position: Qt.vector3d(0,0,2); scale: Qt.vector3d(.34,.415,.47); materials: [fur] }
                        Model { geometry: ear; position: Qt.vector3d(0,4,6); scale: Qt.vector3d(.215,.315,.20); materials: [innerEar] }
                        Model { geometry: ear; position: Qt.vector3d(0,2,9); scale: Qt.vector3d(.055,.12,.08); materials: [lightFur] }
                    }
                    // Cheek ruffs radiate from the head, with continuous soft normals.
                    Model { geometry: head; position: Qt.vector3d(side.modelData*17,-6,22); eulerRotation.z: side.modelData*34; scale: Qt.vector3d(.28,.22,.075); materials: [cream] }
                    Repeater3D {
                        model: 3
                        Model {
                            required property int index
                            geometry: ear; position: Qt.vector3d(side.modelData*(23-index),-index*5,5)
                            eulerRotation.z: side.modelData*(-68-index*12); scale: Qt.vector3d(.09,.18-index*.015,.15); materials: [fur]
                        }
                    }
                    Node {
                        position: Qt.vector3d(side.modelData*11+root.m.yaw*.12,5-root.m.pitch*.10,27)
                        eulerRotation.z: side.modelData*(10+(root.m.action === "error" ? -15 : root.m.action === "needs_input" ? -12 : 0))
                        Model { geometry: sphere; scale: Qt.vector3d(.15,.095,.035); materials: [darkFur] }
                        Model { geometry: sphere; z: 2; scale: Qt.vector3d(.123,(root.m.asleep ? .009 : .075-root.m.joy*.02)*root.m.blink,.035); materials: [eyes] }
                        Model { visible: !root.m.asleep && root.m.blink>.45; geometry: sphere; position: Qt.vector3d(0,0,3.3); scale: Qt.vector3d(.058,.064*root.m.blink,.009); materials: [iris] }
                        Model { visible: !root.m.asleep && root.m.blink>.45; geometry: sphere; position: Qt.vector3d(0,0,3.7); scale: Qt.vector3d(.027,.056*root.m.blink,.008); materials: [eyes] }
                        Model { geometry: sphere; position: Qt.vector3d(0,7,-1); scale: Qt.vector3d(.17,.025,.045); materials: [lightFur] }
                    }
                }
            }
            Model { geometry: head; position: Qt.vector3d(0,-10,28); scale: Qt.vector3d(.235,.16,.29); materials: [cream] }
            Model { geometry: sphere; position: Qt.vector3d(0,-7,43); scale: Qt.vector3d(.105,.072,.07); materials: [nose] }
            Model { geometry: sphere; position: Qt.vector3d(0,-17,35); scale: Qt.vector3d(.115,root.m.action === "speaking" ? .017+root.m.energy*.06 : .012,.045); materials: [nose] }
        }
        Repeater3D {
            model: [40,-46]
            Node {
                id: paw
                required property int modelData
                position: Qt.vector3d(-32+(modelData>0 ? root.m.greeting*8 : root.m.work),modelData+(modelData>0 ? root.m.greeting*8 : 0),45)
                eulerRotation.z: modelData>0 ? root.m.wave*23 : -root.m.work*4
                Model { geometry: sphere; scale: Qt.vector3d(.22,.145,.22); materials: [darkFur] }
                Model { geometry: sphere; x: 4; scale: Qt.vector3d(.18,.135,.18); materials: [fur] }
                Repeater3D {
                    model: 3
                    Model { required property int index; geometry: sphere; position: Qt.vector3d(11,(index-1)*3.5,4); scale: Qt.vector3d(.05,.025,.035); materials: [ivory] }
                }
            }
        }
    }
}
