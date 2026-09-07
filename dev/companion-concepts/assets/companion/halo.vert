// SPDX-License-Identifier: GPL-3.0-or-later
VARYING vec3 n;
VARYING vec3 v;
void MAIN() {
    n=normalize(NORMAL_MATRIX*NORMAL);
    v=CAMERA_POSITION-(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
}
