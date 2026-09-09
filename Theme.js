.pragma library

function toolName(name) {
    // Native tool IDs also occur in saved conversations and must stay stable.
    return /^(peek_computer|mcp__peek__computer|mcp__peek[._]computer|peek[._]computer)$/.test(String(name)) ? "Peek computer" : name
}

function alpha(color, opacity) {
    return Qt.rgba(color.r, color.g, color.b, opacity)
}

function mix(a, b, amount) {
    return Qt.rgba(a.r + (b.r - a.r) * amount, a.g + (b.g - a.g) * amount,
                   a.b + (b.b - a.b) * amount, 1)
}

function luminance(color) {
    function linear(value) { return value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4) }
    return 0.2126 * linear(color.r) + 0.7152 * linear(color.g) + 0.0722 * linear(color.b)
}

function contrast(a, b) {
    var first = luminance(a), second = luminance(b)
    return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05)
}

function readable(background, foreground, surface) {
    var ink = contrast(background, foreground) >= contrast(background, surface) ? foreground : surface
    return Qt.rgba(ink.r, ink.g, ink.b, ink.a)
}
