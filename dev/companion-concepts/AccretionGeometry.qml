// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick3D.Helpers
ProceduralMesh {
    readonly property var mesh: build()
    function build() {
        var p=[],n=[],uv=[],indices=[],slices=128,rings=12;
        for(var j=0;j<=rings;j++) for(var i=0;i<=slices;i++) {
            var a=i/slices*Math.PI*2,r=30+j/rings*24;
            p.push(Qt.vector3d(Math.cos(a)*r,Math.sin(a)*r,0)); n.push(Qt.vector3d(0,0,1)); uv.push(Qt.vector2d(j/rings,i/slices));
        }
        for(var y=0;y<rings;y++) for(var x=0;x<slices;x++) {
            var k=y*(slices+1)+x;indices.push(k,k+slices+1,k+1,k+1,k+slices+1,k+slices+2);
        }
        return {positions:p,normals:n,uvs:uv,indexes:indices};
    }
    positions: mesh.positions; normals: mesh.normals; uv0s: mesh.uvs; indexes: mesh.indexes
}
