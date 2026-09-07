// SPDX-License-Identifier: GPL-3.0-or-later
VARYING vec3 localPosition;
void MAIN() {
    if (swim > 0.0) {
        float t = UV0.y;
        float bend = clock * 2.8 - t * 5.0 + seed;
        VERTEX.x += sin(bend) * t * t * 11.0 * swim;
        VERTEX.z += cos(bend * .8) * t * t * 5.0 * swim;
        NORMAL.y += cos(bend) * t * .12 * swim;
        NORMAL = normalize(NORMAL);
    }
    localPosition = VERTEX;
}
