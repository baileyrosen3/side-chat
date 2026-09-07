import QtQuick

Canvas {
    id: root
    property color fill: "transparent"
    property real corner: 20
    property bool outlineEnabled: true
    property bool keyboardFocus: false
    property var borderColors: []
    property real borderAngle: 0
    property real borderWidth: 1
    readonly property real strokeWidth: keyboardFocus ? Math.max(1, borderWidth) : borderWidth

    onFillChanged: requestPaint()
    onCornerChanged: requestPaint()
    onOutlineEnabledChanged: requestPaint()
    onKeyboardFocusChanged: requestPaint()
    onBorderColorsChanged: requestPaint()
    onBorderAngleChanged: requestPaint()
    onStrokeWidthChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        var c = getContext("2d"), w = width, h = height
        var r = Math.min(corner, w / 2, h / 6)
        c.clearRect(0, 0, w, h)
        if (w <= 0 || h <= 0) return
        c.beginPath()
        c.moveTo(0, 0)
        c.quadraticCurveTo(0, r, r, r)
        c.lineTo(w - r, r)
        c.quadraticCurveTo(w, r, w, 2 * r)
        c.lineTo(w, h - 2 * r)
        c.quadraticCurveTo(w, h - r, w - r, h - r)
        c.lineTo(r, h - r)
        c.quadraticCurveTo(0, h - r, 0, h)
        // Fill and clip close implicitly; leave the stroke open at the monitor edge.
        c.fillStyle = String(fill)
        c.fill()
        if ((outlineEnabled || keyboardFocus) && strokeWidth > 0) {
            c.save()
            // Clip a double-width stroke to keep its full width inside the drawer.
            c.clip()
            var stroke = borderColors.length ? String(borderColors[0]) : "transparent"
            if (borderColors.length > 1) {
                var radians = borderAngle * Math.PI / 180
                var dx = Math.cos(radians), dy = Math.sin(radians)
                var span = (Math.abs(w * dx) + Math.abs(h * dy)) / 2
                stroke = c.createLinearGradient(w / 2 - dx * span, h / 2 - dy * span,
                                                w / 2 + dx * span, h / 2 + dy * span)
                for (var i = 0; i < borderColors.length; i++)
                    stroke.addColorStop(i / (borderColors.length - 1), String(borderColors[i]))
            }
            c.strokeStyle = stroke
            c.lineWidth = strokeWidth * 2
            c.stroke()
            c.restore()
        }
    }
}
