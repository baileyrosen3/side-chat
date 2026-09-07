// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick3D.Helpers

ProceduralMesh {
    readonly property var mesh: build()
    function build() {
        var p=[], n=[], indices=[], segments=80, sides=6;
        for (var i=0;i<=segments;i++) for (var j=0;j<=sides;j++) {
            var a=i/segments*Math.PI*2, b=j/sides*Math.PI*2;
            var radius=47+Math.cos(b)*.65;
            p.push(Qt.vector3d(Math.cos(a)*radius,Math.sin(a)*radius,Math.sin(b)*.65));
            n.push(Qt.vector3d(Math.cos(a)*Math.cos(b),Math.sin(a)*Math.cos(b),Math.sin(b)));
        }
        for (var x=0;x<segments;x++) for (var y=0;y<sides;y++) {
            var k=x*(sides+1)+y;
            indices.push(k,k+sides+1,k+1,k+1,k+sides+1,k+sides+2);
        }
        return {positions:p,normals:n,indexes:indices};
    }
    positions: mesh.positions; normals: mesh.normals; indexes: mesh.indexes
}
