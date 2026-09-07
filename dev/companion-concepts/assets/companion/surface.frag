// SPDX-License-Identifier: GPL-3.0-or-later
VARYING vec3 localPosition;
float hash31(vec3 p) {
    p = fract(p * .1031); p += dot(p, p.yzx + 33.33);
    return fract((p.x + p.y) * p.z);
}
float noise3(vec3 p) {
    vec3 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
    return mix(mix(mix(hash31(i),hash31(i+vec3(1,0,0)),f.x),mix(hash31(i+vec3(0,1,0)),hash31(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash31(i+vec3(0,0,1)),hash31(i+vec3(1,0,1)),f.x),mix(hash31(i+vec3(0,1,1)),hash31(i+vec3(1,1,1)),f.x),f.y),f.z);
}
float fbm(vec3 p) {
    return noise3(p)*.55+noise3(p*2.1)*.26+noise3(p*4.3)*.13+noise3(p*8.5)*.06;
}
void MAIN() {
    vec3 p = localPosition * .025;
    float rim = pow(1.0-abs(dot(normalize(NORMAL), normalize(VIEW_VECTOR))),3.0);
    float grain = noise3(localPosition*3.5);
    BASE_COLOR = vec4(tint.rgb,opacityAmount);
    ROUGHNESS = softness; SPECULAR_AMOUNT=.45;
    if (surfaceStyle < .5) {
        // Fine directional fibres and a warm, soft grazing-angle sheen.
        float fibres=noise3(vec3(UV0.x*720.0,UV0.y*85.0,1.0));
        float variation=fbm(p*3.0)*.32+fibres*.16;
        BASE_COLOR.rgb=mix(tint.rgb,secondary.rgb,variation+rim*.18);
        ROUGHNESS=.72+grain*.12;
        EMISSIVE_COLOR=secondary.rgb*rim*.07;
    } else if (surfaceStyle < 1.5) {
        // Thin-film colour, radial bell ribs, and moving internal caustics.
        float ribs=pow(.5+.5*cos(UV0.x*75.398),18.0);
        float caustic=pow(fbm(p*4.0+vec3(clock*.17,0,-clock*.12)),4.0);
        BASE_COLOR.rgb=mix(tint.rgb,secondary.rgb,rim*.8+caustic*.5);
        ROUGHNESS=.16; METALNESS=.16; CLEARCOAT_AMOUNT=1.0; CLEARCOAT_ROUGHNESS=.12;
        EMISSIVE_COLOR=secondary.rgb*(rim*.75+ribs*.14+caustic*(1.1+energy));
    } else if (surfaceStyle < 2.5) {
        // Advected convection cells, cool fissures, and hot granules.
        vec3 flow=p*3.2+vec3(clock*.12,sin(clock*.3)*.1,-clock*.08);
        float field=fbm(flow+fbm(flow*1.7));
        float cells=smoothstep(.26,.75,field);
        vec3 plasma=mix(tint.rgb*.22,secondary.rgb,cells);
        BASE_COLOR.rgb=plasma;
        EMISSIVE_COLOR=(plasma*(.7+energy*.8)+secondary.rgb*pow(field,5.0)*3.0)*glowAmount;
        ROUGHNESS=.8;
    } else if (surfaceStyle > 3.5) {
        float bands=.45+.55*pow(.5+.5*sin(UV0.x*150.0+noise3(vec3(UV0.x*16.0,1,1))*4.0),2.0);
        float gap=1.0-smoothstep(.012,.023,abs(UV0.x-.67));
        float fade=smoothstep(0.0,.07,UV0.x)*(1.0-smoothstep(.85,1.0,UV0.x));
        BASE_COLOR=vec4(mix(tint.rgb,secondary.rgb,bands),opacityAmount*fade*(1.0-gap*.88));
        METALNESS=.6; ROUGHNESS=.42;
        EMISSIVE_COLOR=secondary.rgb*bands*.14;
    } else {
        float lines=.5+.5*sin(UV0.y*1900.0);
        BASE_COLOR.rgb=tint.rgb*(.92+.08*grain);
        METALNESS=.78; ROUGHNESS=.27+lines*.035;
        CLEARCOAT_AMOUNT=.3; CLEARCOAT_ROUGHNESS=.2;
    }
}
