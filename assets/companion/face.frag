// SPDX-License-Identifier: GPL-3.0-or-later
VARYING vec2 facePosition;
float ellipse(vec2 p,vec2 radius) { return (length(p/radius)-1.0)*min(radius.x,radius.y); }
float stroke(float d,float width) {
    float aa=max(fwidth(d),.002);
    return 1.0-smoothstep(width-aa,width+aa,abs(d));
}
float fill(float d) { float aa=max(fwidth(d),.002); return 1.0-smoothstep(-aa,aa,d); }
void MAIN() {
    vec2 p=facePosition;
    vec3 ink=eyeColor.rgb;
    vec3 pixels=vec3(0);
    for(int i=0;i<2;i++) {
        float side=i==0 ? -1.0 : 1.0;
        float blink=i==0 ? leftBlink : rightBlink;
        float ask=curious*(i==0 ? -.03 : .07);
        vec2 q=p-vec2(side*.34+gazeHorizontal,.18+gazeVertical+ask);
        float width=.145+surprised*.025;
        float height=(.20+surprised*.08-focused*.035-curious*(i==0 ? .065 : -.02))*max(.025,blink);
        float oval=ellipse(q,vec2(width,height));
        float arch=q.y-(.045-.09*q.x*q.x/(width*width));
        float smileEye=stroke(arch,.029)*(1.0-smoothstep(width-.025,width+.005,abs(q.x)));
        float joy=smoothstep(.55,.8,happy)*(1.0-surprised);
        float closed=stroke(q.y+.035-.08*pow(q.x/width,2.0),.014)*(1.0-smoothstep(width-.02,width,abs(q.x)));
        float eye=mix(mix(fill(oval),smileEye,joy),closed,drowsy);
        float halo=exp(-max(oval,0.0)*40.0)*.08*(1.0-drowsy);
        float sparkle=fill(ellipse(q-vec2(-.045,.072),vec2(.027,.022)))*(1.0-joy)*(1.0-drowsy)*blink;
        pixels+=ink*(eye+halo*(1.0-joy))+vec3(.65)*sparkle;
        // Inner brow rises in concern; one brow lifts when asking a question.
        vec2 brow=q-vec2(0,.30+ask+worried*.07);
        float browCurve=brow.y+worried*side*brow.x*.45-curious*side*brow.x*.3+.12*brow.x*brow.x;
        pixels+=ink*stroke(browCurve,.016)*(1.0-smoothstep(.12,.15,abs(brow.x)))*(.22+curious*.55+worried*.5)*(1.0-drowsy);
        // Three tiny amber freckles are Peek's signature.
        for(int j=0;j<3;j++) {
            vec2 dotPos=vec2(side*(.51+float(j)*.06),-.13-float(j%2)*.035);
            pixels+=detailColor.rgb*fill(length(p-dotPos)-.017)*(.25+happy*.3);
        }
    }
    float mouthWidth=.23+happy*.07;
    float curve=p.y+.30+(happy*.13-worried*.09)*(1.0-p.x*p.x/(mouthWidth*mouthWidth));
    float smile=stroke(curve,.023)*(1.0-smoothstep(mouthWidth-.025,mouthWidth,abs(p.x)));
    float opening=talking*(.015+speech*.14)+surprised*.075;
    float openMouth=stroke(ellipse(p-vec2(0,-.34),vec2(.12+speech*.06,.028+opening)),.019);
    float mouth=mix(smile,openMouth,smoothstep(.01,.06,opening));
    mouth=mix(mouth,stroke(ellipse(p-vec2(0,-.31),vec2(.048,.034)),.014),drowsy);
    pixels+=ink*mouth*.85;
    // A barely visible scan texture preserves the feel of a physical display.
    float scan=.97+.03*sin(p.y*450.0);
    BASE_COLOR=vec4(screenColor.rgb,1.0);
    EMISSIVE_COLOR=pixels*scan*(1.0-drowsy*.45);
    ROUGHNESS=.42; SPECULAR_AMOUNT=.07; METALNESS=0.0;
}
