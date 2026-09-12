.pragma library

// Listening in Chat uses Peek; Notes and To-dos produce drafts for review.
function run(chat, action) {
    switch (action) {
    case "chat": case "notes": case "todos": chat.navigate(action); break
    case "listen-chat": chat.toggleChatListening(); break
    case "listen-notes": chat.thoughts.toggleCapture("note"); break
    case "listen-todos": chat.thoughts.toggleCapture("todo"); break
    case "note": chat.thoughts.newNote(); break
    case "selection": chat.workspace.capture(false); break
    case "search": chat.workspace.toggleSearch(); break
    case "workspace": chat.toggle(); break
    case "history": chat.openHistory(); break
    case "settings": chat.openPreferences(); break
    case "peek": chat.setPeek(!chat.peek.enabled, false); break
    case "microphone": chat.toggleMicrophone(); break
    case "record": chat.thoughts.startCapture("note"); break
    case "record-stop": chat.thoughts.stopCapture(); break
    case "stop": chat.stopWorkspace(); break
    case "hide": chat.close(); break
    case "controls": chat.openWorkspacePeek(); break
    }
}
