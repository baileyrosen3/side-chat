// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick3D

Node {
    id: root
    required property var motion
    readonly property var m: motion
    SculptGeometry { id: sphere }
    OrbitRing { id: ring }
    AccretionGeometry { id: disk }
    CompanionMaterial { id: star; surfaceStyle: 2; tint: root.m.action === "error" ? "#53101b" : "#a8310d"; secondary: "#ed9541"; clock: root.m.cycle; energy: root.m.energy }
    CompanionMaterial { id: ice; surfaceStyle: 2; tint: "#072c48"; secondary: "#76b4c6"; glowAmount: 0; clock: root.m.cycle*.12 }
    CompanionMaterial { id: stone; surfaceStyle: 2; tint: "#232036"; secondary: "#ad9dbe"; glowAmount: 0 }
    CompanionMaterial { id: dust; surfaceStyle: 4; tint: "#6e402b"; secondary: "#b79e76"; opacityAmount: .54 }
    PrincipledMaterial { id: metal; baseColor: "#ae9a78"; metalness: .8; roughness: .25 }
    PrincipledMaterial { id: night; baseColor: "#151826"; roughness: .72 }
    PrincipledMaterial { id: light; baseColor: "#f8d39a"; emissiveFactor: Qt.vector3d(.7,.35,.1); roughness: .2 }
    CompanionHalo { id: corona; tint: "#ffb651"; strength: .72+root.m.energy*.2+root.m.joy*.4 }
    Node {
        x: -85*(1-root.m.arrival)-1+root.m.lean*6
        y: 3+root.m.breathe*1.2+root.m.waking*5+root.m.lift*6-root.m.landing*5
        eulerRotation: Qt.vector3d(root.m.pitch*.5,root.m.yaw*.5,root.m.shake*8+root.m.wave*10+root.m.attention*10)
        Node {
            scale: Qt.vector3d(1+root.m.energy*.09+root.m.joy*.10-root.m.sleep*.12,1+root.m.energy*.09+root.m.joy*.10-root.m.sleep*.12,1)
            Model { geometry: sphere; scale: Qt.vector3d(.47,.47,.47); materials: [star] }
            Model { geometry: sphere; scale: Qt.vector3d(.59,.59,.59); materials: [corona] }
            Model {
                geometry: sphere; position: Qt.vector3d(-44*root.m.blink*(1-root.m.sleep)+5*root.m.sleep,2,26)
                visible: root.m.blink<.98 || root.m.sleep>.01; scale: Qt.vector3d(.43,.43,.18); materials: [night]
            }
        }
        Node {
            eulerRotation: Qt.vector3d(61-root.m.sleep*15+root.m.scan*8,14+root.m.greeting*18+root.m.lift*16,-24+root.m.greeting*22+root.m.warming*8)
            scale: Qt.vector3d(1+root.m.joy*.18+root.m.energy*.04,1+root.m.joy*.18+root.m.energy*.04,1)
            Model { geometry: disk; materials: [dust] }
            Model { geometry: ring; scale: Qt.vector3d(1.15,1.15,.6); materials: [metal] }
        }
        Repeater3D {
            model: 3
            Node {
                id: orbit
                required property int index
                readonly property real spin: root.m.orbitPhase*(index%2 ? -.8 : .6)+index*2.1
                readonly property real radius: 40+index*5+root.m.joy*13
                eulerRotation: Qt.vector3d(12+index*33-root.m.sleep*20,10+index*35+root.m.greeting*30,index*53+root.m.attention*8)
                Model { visible: orbit.index === 1; geometry: ring; scale: Qt.vector3d(1.02,1.02,.4); opacity: .4; materials: [metal] }
                Model {
                    geometry: sphere; position: Qt.vector3d(Math.cos(orbit.spin)*orbit.radius,Math.sin(orbit.spin)*orbit.radius,0)
                    scale: Qt.vector3d(index === 1 ? .11 : .066,index === 1 ? .11 : .066,index === 1 ? .11 : .066)
                    materials: index === 1 ? [ice] : [stone]
                }
                Repeater3D {
                    model: 9
                    Model {
                        required property int index
                        readonly property real angle: orbit.spin-(index+1)*.045
                        geometry: sphere; position: Qt.vector3d(Math.cos(angle)*orbit.radius,Math.sin(angle)*orbit.radius,0)
                        scale: Qt.vector3d(.008-index*.0006,.008-index*.0006,.008-index*.0006)
                        opacity: root.m.asleep ? .05 : .5-index*.045; materials: [light]
                    }
                }
            }
        }
        Repeater3D {
            model: 16
            Node {
                required property int index
                eulerRotation.z: index*22.5+root.m.cycle*8
                Model {
                    geometry: sphere; y: 26+root.m.joy*(20+index%3*5)+root.m.warming*4
                    scale: Qt.vector3d(.007,.025+root.m.joy*.065+root.m.warming*.018,.007)
                    opacity: .2+root.m.joy*.7-root.m.sleep*.18; materials: [light]
                }
            }
        }
    }
}
