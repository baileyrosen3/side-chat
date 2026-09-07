// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick3D.Helpers

// Smooth, UV-mapped surfaces with derivative normals. Geometry is built once;
// movement is handled by the rig or GPU, never by rebuilding the mesh per frame.
ProceduralMesh {
    property string shape: "sphere"
    property int slices: 64
    property int stacks: 40
    readonly property var mesh: build()
    function point(u,v) {
        var a=u*Math.PI*2, b=v*Math.PI;
        if (shape === "ear") {
            var r=Math.pow(Math.sin(b),.9)*(1-v*.84);
            return Qt.vector3d(Math.cos(a)*r*50+v*v*13,v*100,Math.sin(a)*r*19);
        }
        if (shape === "bell") {
            var t=v*Math.PI*.57, r=Math.sin(t)*(1+.035*Math.cos(a*12)*Math.pow(v,4));
            return Qt.vector3d(Math.cos(a)*r*50,Math.cos(t)*43,Math.sin(a)*r*50);
        }
        if (shape === "ribbon") {
            var taper=Math.pow(1-v,.6), angle=u*Math.PI*2;
            var sweep=Math.sin(v*7)*v*8;
            return Qt.vector3d(Math.cos(angle)*taper*3.3+sweep,-v*100,Math.sin(angle)*taper*.65+Math.sin(v*9)*v*2);
        }
        var radius=Math.sin(b)*50;
        if (shape === "head") radius*=1+.12*Math.exp(-Math.pow((v-.63)*7,2));
        return Qt.vector3d(Math.cos(a)*radius,Math.cos(b)*50,Math.sin(a)*radius);
    }
    function build() {
        var p=[],n=[],uv=[],indices=[],eps=.0001;
        for (var j=0;j<=stacks;j++) for (var i=0;i<=slices;i++) {
            var u=i/slices,v=j/stacks,vc=Math.max(eps,Math.min(1-eps,v));
            var a=point(u-eps,vc),b=point(u+eps,vc),c=point(u,vc-eps),d=point(u,vc+eps);
            var du=Qt.vector3d(b.x-a.x,b.y-a.y,b.z-a.z),dv=Qt.vector3d(d.x-c.x,d.y-c.y,d.z-c.z);
            var nx=du.y*dv.z-du.z*dv.y,ny=du.z*dv.x-du.x*dv.z,nz=du.x*dv.y-du.y*dv.x;
            var flip=shape === "ear" ? -1 : 1;
            var len=Math.max(.0000001,Math.hypot(nx,ny,nz));
            p.push(point(u,v)); n.push(Qt.vector3d(flip*nx/len,flip*ny/len,flip*nz/len));uv.push(Qt.vector2d(u,v));
        }
        for (var y=0;y<stacks;y++) for (var x=0;x<slices;x++) {
            var k=y*(slices+1)+x;
            if (shape === "ear") indices.push(k,k+slices+1,k+1,k+1,k+slices+1,k+slices+2);
            else indices.push(k,k+1,k+slices+1,k+1,k+slices+2,k+slices+1);
        }
        return {positions:p,normals:n,uvs:uv,indexes:indices};
    }
    positions: mesh.positions; normals: mesh.normals; uv0s: mesh.uvs; indexes: mesh.indexes
}
