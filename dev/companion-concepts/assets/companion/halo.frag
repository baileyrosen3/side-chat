// SPDX-License-Identifier: GPL-3.0-or-later
VARYING vec3 n;
VARYING vec3 v;
void MAIN() {
    float facing=abs(dot(normalize(n),normalize(v)));
    float corona=pow(1.0-facing,3.5)*smoothstep(0.0,.22,facing);
    FRAGCOLOR=vec4(tint.rgb*1.5,corona*strength);
}
