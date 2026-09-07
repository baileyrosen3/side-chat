.pragma library
function label(v, busy) {
    if (v.preview) return "Preview · no mic"
    if (v.error) return "Needs attention"
    if (!v.ready) return "Waking up"
    if (v.hearing) return "Listening to you"
    if (v.transcribing) return "Understanding"
    if (v.stage === "needs_input") return "Your turn"
    if (v.speaking) return "Speaking"
    if (v.stage === "acting") return "Working"
    if (busy || v.stage === "thinking") return "Thinking"
    if (v.standby) return "On standby"
    return v.listening ? "Listening" : "Microphone off"
}
