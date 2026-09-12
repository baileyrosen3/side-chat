import QtQuick
import qs.Commons

Canvas {
    id: root
    ChatStyle { id: ui }
    property string name: ""
    property color ink: ui.foreground
    implicitWidth: Style.space(15)
    implicitHeight: implicitWidth
    onNameChanged: requestPaint()
    onInkChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        var c = getContext("2d")
        c.reset(); c.clearRect(0, 0, width, height)
        c.scale(width / 24, height / 24)
        c.strokeStyle = String(ink); c.fillStyle = String(ink)
        c.lineWidth = 1.8; c.lineCap = "square"; c.lineJoin = "miter"
        function line(x1,y1,x2,y2) { c.moveTo(x1,y1); c.lineTo(x2,y2) }
        c.beginPath()
        switch (name) {
        case "bell": c.moveTo(5,17);c.lineTo(7,14);c.lineTo(7,9);c.arc(12,9,5,Math.PI,Math.PI*2);c.lineTo(17,14);c.lineTo(19,17);c.closePath();c.moveTo(10,20);c.quadraticCurveTo(12,23,14,20);line(12,2,12,4);break
        case "thought": c.moveTo(9,17);c.bezierCurveTo(9,14,5,13,5,9);c.bezierCurveTo(5,0,19,0,19,9);c.bezierCurveTo(19,13,15,14,15,17);c.closePath();line(9,20,15,20);line(11,23,13,23);line(12,17,12,10);line(9,8,12,11);line(15,8,12,11);break
        case "pin": c.moveTo(8,3);c.lineTo(16,3);c.lineTo(15,10);c.lineTo(19,14);c.lineTo(5,14);c.lineTo(9,10);c.closePath();line(12,14,12,22);break
        case "archive": c.rect(3,4,18,4);c.rect(5,8,14,12);line(10,12,14,12);break
        case "tag": c.moveTo(3,3);c.lineTo(12,3);c.lineTo(21,12);c.lineTo(12,21);c.lineTo(3,12);c.closePath();c.moveTo(9,7);c.arc(8,7,1,0,Math.PI*2);break
        case "read": c.moveTo(12,6);c.quadraticCurveTo(7,3,3,5);c.lineTo(3,19);c.quadraticCurveTo(7,17,12,20);c.quadraticCurveTo(17,17,21,19);c.lineTo(21,5);c.quadraticCurveTo(17,3,12,6);c.lineTo(12,20);break
        case "orb": c.roundedRect(5,6,14,12,4,4); line(9,10,9,13); line(15,10,15,13); line(17,6,18,3); line(2,10,2,14); line(22,10,22,14); break
        case "power": c.arc(12,13,8,-Math.PI*.3,Math.PI*1.3); line(12,2,12,12);break
        case "sleep": c.moveTo(17,3);c.bezierCurveTo(1,0,1,23,17,21);c.bezierCurveTo(8,17,8,7,17,3);break
        case "desktop": c.roundedRect(3,4,18,13,2,2);line(12,17,12,21);line(8,21,16,21);break
        case "globe": c.ellipse(3,3,18,18);c.ellipse(8,3,8,18);line(3,12,21,12);break
        case "volume": case "muted": c.moveTo(3,9);c.lineTo(7,9);c.lineTo(12,5);c.lineTo(12,19);c.lineTo(7,15);c.lineTo(3,15);c.closePath();if(name === "muted") {line(16,9,22,15);line(22,9,16,15)} else {c.moveTo(16,8);c.quadraticCurveTo(21,12,16,16);c.moveTo(19,5);c.quadraticCurveTo(27,12,19,19)}break
        case "mic": c.roundedRect(9,3,6,11,3,3); c.stroke(); c.beginPath(); c.arc(12,11,6,0,Math.PI); line(6,9,6,11); line(18,9,18,11); line(12,17,12,21); line(9,21,15,21); break
        case "mic-off": c.arc(12,11,6,0,Math.PI); line(12,17,12,21); line(9,21,15,21); line(4,4,20,20); c.moveTo(9,7);c.lineTo(9,6);c.arc(12,6,3,Math.PI,Math.PI*2);c.lineTo(15,11);break
        case "chat": c.moveTo(4,4);c.lineTo(20,4);c.lineTo(20,16);c.lineTo(10,16);c.lineTo(4,21);c.closePath();line(8,9,16,9);line(8,12,13,12);break
        case "new": line(12,5,12,19); line(5,12,19,12); break
        case "terminal": c.rect(3,4,18,16); line(7,9,10,12); line(10,12,7,15); line(13,15,17,15); break
        case "close": line(7,7,17,17); line(17,7,7,17); break
        case "send": line(12,19,12,5); line(6,11,12,5); line(12,5,18,11); break
        case "down": line(12,5,12,19); line(6,13,12,19); line(12,19,18,13); break
        case "chevron-down": c.moveTo(6,9); c.lineTo(12,15); c.lineTo(18,9); break
        case "chevron-up": c.moveTo(6,15); c.lineTo(12,9); c.lineTo(18,15); break
        case "chevron-right": c.moveTo(9,6); c.lineTo(15,12); c.lineTo(9,18); break
        case "stop": c.rect(7,7,10,10); c.fill(); break
        case "check": c.moveTo(5,12); c.lineTo(10,17); c.lineTo(19,7); break
        case "copy": c.rect(8,8,12,12); c.moveTo(15,4); c.lineTo(4,4); c.lineTo(4,15); break
        case "history": c.arc(12,12,8,Math.PI*1.17,Math.PI*3); line(12,8,12,12); line(12,12,15,14); line(4,4,4,9); line(4,9,9,9); break
        case "settings": line(5,6,19,6); line(5,12,19,12); line(5,18,19,18); c.stroke(); c.beginPath(); c.rect(8,4,3,4); c.rect(14,10,3,4); c.rect(8,16,3,4); break
        case "expand": line(9,4,4,4); line(4,4,4,9); line(15,4,20,4); line(20,4,20,9); line(4,15,4,20); line(4,20,9,20); line(20,15,20,20); line(20,20,15,20); break
        case "collapse": line(4,9,9,9); line(9,9,9,4); line(15,4,15,9); line(15,9,20,9); line(4,15,9,15); line(9,15,9,20); line(15,20,15,15); line(15,15,20,15); break
        case "back": line(19,12,5,12); line(5,12,11,6); line(5,12,11,18); break
        case "edit": c.moveTo(5,15); c.lineTo(15,5); c.quadraticCurveTo(17,3,19,5); c.quadraticCurveTo(21,7,19,9); c.lineTo(9,19); c.lineTo(4,20); c.closePath(); line(14,6,18,10); break
        case "retry": c.arc(12,12,8,Math.PI*.15,Math.PI*1.85); line(20,4,20,9); line(20,9,15,9); break
        case "attach": c.moveTo(8,12); c.lineTo(14,6); c.bezierCurveTo(18,2,23,7,19,11); c.lineTo(10,20); c.bezierCurveTo(5,25,0,18,5,13); c.lineTo(14,4); c.stroke(); c.beginPath(); c.moveTo(8,12); c.bezierCurveTo(5,15,9,19,12,16); c.lineTo(17,11); break
        case "clipboard": c.rect(5,5,14,16); c.rect(9,3,6,4); line(9,12,15,12); line(9,16,13,16); break
        case "export": c.moveTo(5,14); c.lineTo(5,20); c.lineTo(19,20); c.lineTo(19,14); line(12,15,12,3); line(7,8,12,3); line(12,3,17,8); break
        case "folder": c.moveTo(3,7); c.lineTo(3,19); c.lineTo(21,19); c.lineTo(21,7); c.lineTo(12,7); c.lineTo(10,4); c.lineTo(3,4); c.closePath(); break
        case "shield": c.moveTo(12,3); c.lineTo(20,6); c.lineTo(19,14); c.quadraticCurveTo(17,19,12,22); c.quadraticCurveTo(7,19,5,14); c.lineTo(4,6); c.closePath(); line(8,12,11,15); line(11,15,16,9); break
        case "search": c.arc(10.5,10.5,6.5,0,Math.PI*2); line(15.5,15.5,21,21); break
        case "trash": line(4,7,20,7); line(9,7,9,4); line(9,4,15,4); line(15,4,15,7); c.moveTo(6,7); c.lineTo(7,20); c.lineTo(17,20); c.lineTo(18,7); line(10,11,10,17); line(14,11,14,17); break
        case "external": c.moveTo(10,5); c.lineTo(4,5); c.lineTo(4,20); c.lineTo(19,20); c.lineTo(19,14); line(20,4,11,13); line(14,4,20,4); line(20,4,20,10); break
        }
        c.stroke()
    }
}
