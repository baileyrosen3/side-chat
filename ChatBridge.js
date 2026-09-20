.pragma library

// One service owns the backend. Bar instances share it, including when Island
// embeds their popup content. Registration works in either QML load order.
var service = null
var panels = []

function sync() {
    if (service) service.panels = panels.slice()
    panels.forEach(function(panel) { panel.chat = service })
}

function setService(value) {
    service = value
    sync()
}

function clearService(value) {
    if (service !== value) return
    service = null
    sync()
}

function add(panel) {
    if (panels.indexOf(panel) < 0) panels.push(panel)
    sync()
}

function remove(panel) {
    panels = panels.filter(function(item) { return item !== panel })
    sync()
}
