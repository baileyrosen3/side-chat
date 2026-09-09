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
        float width=.145+surprised*.035+listening*.012+hearing*speech*.012;
        float height=(.20+surprised*.10+listening*.025+hearing*speech*.025-focused*.055-curious*(i==0 ? .065 : -.025))*max(.025,blink);
        float oval=ellipse(q,vec2(width,height));
        float arch=q.y-(.045-.09*q.x*q.x/(width*width));
        float smileEye=stroke(arch,.029)*(1.0-smoothstep(width-.025,width+.005,abs(q.x)));
        float joy=smoothstep(.65,.9,happy)*(1.0-smoothstep(.25,.6,surprised));
        float closed=stroke(q.y+.035-.08*pow(q.x/width,2.0),.014)*(1.0-smoothstep(width-.02,width,abs(q.x)));
        float eye=mix(mix(fill(oval),smileEye,joy),closed,drowsy);
        float bootEye=stroke(q.y-.03*sin(clock*2.0+side),.028)*(1.0-smoothstep(width-.02,width,abs(q.x)));
        eye=mix(eye,bootEye,booting*.8);
        float halo=exp(-max(oval,0.0)*28.0)*(.10+listening*(.04+speech*.10)+readyBurst*.10)*(1.0-drowsy);
        float sparkle=fill(ellipse(q-vec2(-.045,.072),vec2(.027,.022)))*(1.0-joy)*(1.0-drowsy)*blink;
        pixels+=ink*(eye+halo*(1.0-joy))+vec3(.65)*sparkle;
        // Inner brow rises in concern; one brow lifts when asking a question.
        vec2 brow=q-vec2(0,.30+ask+worried*.07);
        float browCurve=brow.y+worried*side*brow.x*.45-curious*side*brow.x*.3+.12*brow.x*brow.x;
        pixels+=ink*stroke(browCurve,.020)*(1.0-smoothstep(.12,.16,abs(brow.x)))*(.25+curious*.6+worried*.6)*(1.0-drowsy);
        // Freckles brighten in the current expression's color.
        for(int j=0;j<3;j++) {
            vec2 dotPos=vec2(side*(.51+float(j)*.06),-.13-float(j%2)*.035);
            pixels+=detailColor.rgb*fill(length(p-dotPos)-(.018+celebrating*.004))*(.35+happy*.45+hearing*speech*.2);
        }
        vec2 glint=p-vec2(side*.66,.40+.04*sin(clock*2.0+side));
        float star=min(abs(glint.x)+abs(glint.y)*.25,abs(glint.y)+abs(glint.x)*.25);
        pixels+=detailColor.rgb*fill(star-.012)*(1.0-smoothstep(.04,.085,length(glint)))*celebrating*(.4+.3*signalPulse);
    }
    float mouthWidth=.23+happy*.10;
    float curve=p.y+.30+(happy*.19-worried*.14)*(1.0-p.x*p.x/(mouthWidth*mouthWidth));
    float smile=stroke(curve,.023)*(1.0-smoothstep(mouthWidth-.025,mouthWidth,abs(p.x)));
    float opening=talking*(.02+speech*.18)+surprised*.085;
    float openMouth=stroke(ellipse(p-vec2(0,-.34),vec2(.11+speech*.09,.028+opening)),.023);
    float mouth=mix(smile,openMouth,smoothstep(.01,.06,opening));
    mouth=mix(mouth,stroke(ellipse(p-vec2(0,-.31),vec2(.048,.034)),.014),drowsy);
    pixels+=ink*mouth*.85;
    // A small microphone meter uses measured audio; quiet listening retains
    // a steady baseline. It never animates the mouth as if Peek were speaking.
    for(int j=0;j<5;j++) {
        vec2 bar=p-vec2((float(j)-2.0)*.085,-.66);
        float barHeight=.014+speech*(.04+.05*(.5+.5*sin(clock*7.0+float(j)*1.4)));
        float meter=fill(max(abs(bar.x)-.019,abs(bar.y)-barHeight));
        pixels+=ink*meter*listening*(.45+.25*signalPulse);
    }
    for(int j=0;j<3;j++) {
        vec2 dot=p-vec2((float(j)-1.0)*.14,-.64);
        float glow=.25+.65*pow(.5+.5*sin(clock*4.0-float(j)*1.8),2.0);
        pixels+=ink*fill(length(dot)-.025)*booting*glow;
    }
    // A barely visible scan texture preserves the feel of a physical display.
    float scan=.97+.03*sin(p.y*450.0);
    BASE_COLOR=vec4(screenColor.rgb,1.0);
    EMISSIVE_COLOR=pixels*scan*(1.0-drowsy*.45);
    ROUGHNESS=.42; SPECULAR_AMOUNT=.07; METALNESS=0.0;
}
