// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick3D

Node {
    id: root
    required property var motion
    readonly property var m: motion
    SculptGeometry { id: dome; shape: "bell" }
    SculptGeometry { id: sphere }
    SculptGeometry { id: ribbon; shape: "ribbon"; stacks: 52; slices: 12 }
    OrbitRing { id: ring }
    CompanionMaterial { id: membrane; surfaceStyle: 1; tint: "#1c304c"; secondary: root.m.action === "error" ? "#ee83ad" : "#8de7f4"; clock: root.m.cycle; energy: root.m.energy; opacityAmount: .88 }
    CompanionMaterial { id: heart; surfaceStyle: 1; tint: "#4f3972"; secondary: "#d7a7f8"; clock: root.m.cycle; energy: root.m.energy }
    PrincipledMaterial { id: glow; baseColor: "#9ad9ed"; emissiveFactor: Qt.vector3d(.22,.5,.7); roughness: .2; metalness: .25 }
    PrincipledMaterial { id: eyes; baseColor: "#09202e"; roughness: .1; clearcoatAmount: 1 }
    CompanionHalo { id: aura; tint: "#75cae8"; strength: .35 }
    Node {
        x: -76*(1-root.m.arrival)-5+root.m.lean*12+root.m.shake*4
        y: 10+root.m.breathe*3+root.m.joy*12+root.m.waking*8+root.m.lift*9-root.m.sleep*10-root.m.landing*7
        eulerRotation: Qt.vector3d(root.m.pitch*.5,root.m.yaw*.6,root.m.scan*7+root.m.attention*11+root.m.wave*8+root.m.work*3)
        Node {
            scale: Qt.vector3d(1+root.m.breathe*.025+root.m.energy*.065,1-root.m.breathe*.035-root.m.energy*.06-root.m.sleep*.14+root.m.waking*.1,1)
            Model { geometry: sphere; position: Qt.vector3d(0,9,0); scale: Qt.vector3d(.37,.34,.34); materials: [heart] }
            Model { geometry: dome; scale: Qt.vector3d(.78,.84,.56); materials: [membrane] }
            Model { geometry: sphere; position: Qt.vector3d(0,15,0); scale: Qt.vector3d(.82,.63,.59); materials: [aura] }
            Model { geometry: ring; y: -7; eulerRotation.x: 90; scale: Qt.vector3d(.79,.56,1); materials: [glow] }
            Repeater3D {
                model: 12
                Model {
                    required property int index
                    geometry: sphere
                    position: Qt.vector3d(Math.cos(index*Math.PI/6)*35,-8,Math.sin(index*Math.PI/6)*25)
                    scale: Qt.vector3d(.052,.035,.045); materials: [glow]
                }
            }
            Repeater3D {
                model: [-1,1]
                Model {
                    required property int modelData
                    geometry: sphere; position: Qt.vector3d(modelData*10+root.m.yaw*.1,7-root.m.pitch*.1,26)
                    eulerRotation.z: modelData*(root.m.action === "needs_input" ? -16 : 8)
                    scale: Qt.vector3d(.09,(root.m.asleep ? .009 : .085-root.m.joy*.025)*root.m.blink,.025); materials: [eyes]
                }
            }
            Model { geometry: sphere; position: Qt.vector3d(0,-1,27); scale: Qt.vector3d(.045,root.m.action === "speaking" ? .012+root.m.energy*.055 : .009,.02); materials: [eyes] }
        }
        // Continuous translucent ribbons with GPU deformation; no bead joints.
        Repeater3D {
            model: 9
            Node {
                id: strand
                required property int index
                position: Qt.vector3d((index-4)*6.5,-10,index%2 ? 5 : -5)
                eulerRotation.z: (index-4)*(root.m.joy*4+root.m.greeting*3+root.m.lift*3-root.m.sleep*2)+root.m.wave*(index%2 ? 7 : -7)
                Model {
                    geometry: ribbon; scale: Qt.vector3d(index%2 ? .9 : .55,.40+(index%3)*.075,1)
                    materials: CompanionMaterial {
                        surfaceStyle: 1; tint: strand.index%2 ? "#353d65" : "#346477"; secondary: "#9ae8f3"
                        clock: root.m.cycle; swim: root.m.amount*(.75+root.m.energy*.5); seed: strand.index*.7
                        opacityAmount: .8
                    }
                }
            }
        }
        Repeater3D {
            model: 8
            Model {
                required property int index
                readonly property real angle: root.m.cycle+index*Math.PI/4
                readonly property real radius: 43+root.m.joy*16+root.m.energy*4
                geometry: sphere
                position: Qt.vector3d(Math.cos(angle)*radius,Math.sin(angle)*radius*.8,Math.sin(index*5)*12)
                scale: Qt.vector3d(.009+root.m.joy*.012+root.m.warming*.006,.009+root.m.joy*.012+root.m.warming*.006,.009)
                opacity: root.m.asleep ? .1 : .5+root.m.joy*.4; materials: [glow]
            }
        }
    }
}
