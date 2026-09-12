.pragma library

function title(note) {
    var first=String(note.body || "").trim().split("\n")[0]
    return first.replace(/^#+\s*/, "") || "Untitled note"
}
function matches(note, query) {
    return String(query || "").toLowerCase().trim().split(/\s+/).every(function(term) {
        return (String(note.title || "")+" "+String(note.body || "")).toLowerCase().indexOf(term)>=0
    })
}
function rows(notes, drafts, kind, query, completed) {
    var result=[], used={}
    notes.forEach(function(n) {
        if (n.trashed || (n.kind || "note")!==kind || !!n.done!==completed) return
        var draft=Object.values(drafts).find(function(d) {return d.id===n.id})
        if (draft) {used[draft.key]=true;n=Object.assign({},n,draft,{isDraft:true})}
        if (matches(n,query)) result.push(n)
    })
    if (!completed) Object.keys(drafts).forEach(function(key) {
        var d=drafts[key]
        if (!used[key] && !notes.some(function(n){return n.id===d.id}) && (d.kind || "note")===kind && d.body.trim() && matches(d,query))
            result.push(Object.assign({},d,{isDraft:true,created:new Date(d.updated*1000).toISOString()}))
    })
    return result.sort(function(a,b) {return String(b.created).localeCompare(String(a.created)) || String(b.id || b.key).localeCompare(String(a.id || a.key))})
}
