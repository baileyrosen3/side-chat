// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick3D.Helpers

ProceduralMesh {
    property real corner: 24
    readonly property var mesh: build()

    function build() {
        var p = [], normals = [], indices = [], count = 20;
        var faces = [[[1, 0, 0], [0, 0, -1], [0, 1, 0]], [[-1, 0, 0], [0, 0, 1], [0, 1, 0]], [[0, 1, 0], [1, 0, 0], [0, 0, -1]], [[0, -1, 0], [1, 0, 0], [0, 0, 1]], [[0, 0, 1], [1, 0, 0], [0, 1, 0]], [[0, 0, -1], [-1, 0, 0], [0, 1, 0]]];
        for (var face of faces) {
            var start = p.length;
            for (var y = 0; y <= count; y++) for (var x = 0; x <= count; x++) {
                var a = [], n = [];
                for (var k = 0; k < 3; k++) {
                    a[k] = face[0][k] * 50 + face[1][k] * (x / count - 0.5) * 100 + face[2][k] * (y / count - 0.5) * 100;
                    var inner = Math.max(-50 + corner, Math.min(50 - corner, a[k]));
                    n[k] = a[k] - inner;
                    a[k] = inner;
                }
                var length = Math.hypot(n[0], n[1], n[2]);
                p.push(Qt.vector3d(a[0] + corner * n[0] / length, a[1] + corner * n[1] / length, a[2] + corner * n[2] / length));
                normals.push(Qt.vector3d(n[0] / length, n[1] / length, n[2] / length));
            }
            for (var j = 0; j < count; j++) for (var i = 0; i < count; i++) {
                var b = start + j * (count + 1) + i;
                indices.push(b, b + 1, b + count + 2, b, b + count + 2, b + count + 1);
            }
        }
        return {
            "positions": p,
            "normals": normals,
            "indexes": indices
        };
    }

    positions: mesh.positions
    normals: mesh.normals
    indexes: mesh.indexes
}
