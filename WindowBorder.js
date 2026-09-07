// hyprctl emits ARGB stops; retain alpha and the desktop gradient direction.
function parseGradient(raw) {
    if (typeof raw !== "string") return null
    var parts = raw.trim().split(/\s+/)
    var colors = [], angle = 0
    if (parts.length > 33) return null
    for (var i = 0; i < parts.length; i++) {
        var part = parts[i]
        if (/^-?\d+(?:\.\d+)?deg$/.test(part) && i === parts.length - 1) {
            angle = Number(part.slice(0, -3))
            if (!isFinite(angle)) return null
        } else if (/^[0-9a-fA-F]{8}$/.test(part)) {
            colors.push(Qt.rgba(parseInt(part.slice(2, 4), 16) / 255,
                                parseInt(part.slice(4, 6), 16) / 255,
                                parseInt(part.slice(6, 8), 16) / 255,
                                parseInt(part.slice(0, 2), 16) / 255))
        } else return null
    }
    return colors.length > 0 && colors.length <= 32 ? {colors: colors, angle: angle} : null
}

function parseWidth(value) {
    return typeof value === "number" && isFinite(value) && value >= 0 ? Math.min(100, value) : -1
}
