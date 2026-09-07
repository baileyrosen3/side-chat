.pragma library

function blocks(source) {
    var lines = source.split("\n"), result = [], buffer = [], fence = "", language = ""
    function flush() {
        if (buffer.length) result.push({code: fence !== "", language: language, text: buffer.join("\n")})
        buffer = []
    }
    for (var i = 0; i < lines.length; ++i) {
        var match = lines[i].match(/^ {0,3}(`{3,}|~{3,})(.*)$/)
        if (!fence && match) {
            flush(); fence = match[1]; language = match[2].trim()
        } else if (fence && match && match[1][0] === fence[0] && match[1].length >= fence.length && !match[2].trim()) {
            flush(); fence = ""; language = ""
        } else buffer.push(lines[i])
    }
    flush()
    return result
}
